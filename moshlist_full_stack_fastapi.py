
import os
from collections import Counter

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="MOSHLIST")

SETLIST_API_KEY = os.getenv(
    "SETLIST_API_KEY",
    "Ub2-ndhLiZsRDqrNdoPjaRXZvjlmCZ8kl80j"
)

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MOSHLIST</title>

<style>
body{
    margin:0;
    background:#0b0b0b;
    color:#fff;
    font-family:Arial,sans-serif;
    display:flex;
    justify-content:center;
    align-items:center;
    min-height:100vh;
}

.wrap{
    width:92%;
    max-width:820px;
    background:#161616;
    padding:32px;
    border-radius:20px;
    box-shadow:0 0 28px rgba(0,0,0,.45);
}

h1{
    text-align:center;
    font-size:3rem;
    margin:0;
}

.sub{
    text-align:center;
    color:#aaa;
    margin:8px 0 24px;
}

.row{
    display:flex;
    gap:12px;
    flex-wrap:wrap;
}

input{
    flex:1;
    min-width:240px;
    padding:14px;
    border-radius:12px;
    border:1px solid #333;
    background:#0e0e0e;
    color:#fff;
}

button{
    padding:14px 20px;
    border:none;
    border-radius:12px;
    background:#e11d48;
    color:#fff;
    font-weight:700;
    cursor:pointer;
}

#out{
    display:none;
    margin-top:24px;
    background:#101010;
    padding:20px;
    border-radius:16px;
}

ol{
    line-height:1.8;
}

.small{
    color:#777;
}
</style>
</head>

<body>

<div class="wrap">

<h1>MOSHLIST</h1>

<div class="sub">
Live tour setlists turned into playlists.
</div>

<div class="row">
<input id="band" placeholder="Enter band name">
<button onclick="go()">Generate</button>
</div>

<div id="out">
<h2 id="title"></h2>
<ol id="songs"></ol>
<div class="small">
Spotify export coming soon.
</div>
</div>

</div>

<script>

async function go(){

    const band = document.getElementById('band').value.trim();

    if(!band) return;

    const r = await fetch(
        '/api/playlist?band=' +
        encodeURIComponent(band)
    );

    const data = await r.json();

    document.getElementById('title').textContent =
        data.title;

    document.getElementById('songs').innerHTML =
        data.songs.map(
            s => '<li>' + s + '</li>'
        ).join('');

    document.getElementById('out').style.display =
        'block';
}

</script>

</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML


@app.get("/api/playlist")
def playlist(
    band: str = Query(...)
):
    songs = get_current_setlist(band)

    return JSONResponse({
        "title": f"{band} Current Tour Playlist",
        "songs": songs
    })


def ensure_list(value):

    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]

CACHE = {}

def get_current_setlist(band: str):

    # -------------------------------
    # SIMPLE CACHE
    # -------------------------------

    cache_key = band.lower().strip()

    if cache_key in CACHE:
        return CACHE[cache_key]

    headers = {
        "x-api-key": SETLIST_API_KEY,
        "Accept": "application/json",
        "User-Agent": "MOSHLIST/1.0"
    }


    # -----------------------------------
    # SEARCH ARTISTS
    # -----------------------------------

    artist_response = requests.get(
        "https://api.setlist.fm/rest/1.0/search/artists",
        params={
            "artistName": band,
            "p": 1
        },
        headers=headers,
        timeout=15
    )

    if artist_response.status_code == 429:
        return [
            "Rate limited by Setlist.fm. Try again shortly."
        ]

    artist_data = artist_response.json()

    artists = ensure_list(
        artist_data.get("artist")
    )

    if not artists:
        return [
            "Band not found"
        ]


    # -----------------------------------
    # FIND BEST MATCH
    # -----------------------------------

    best_artist = None

    search_name = band.lower().strip()

    # Exact name matches
    matching_artists = []

    for artist in artists:

        artist_name = (
            artist.get("name", "")
            .lower()
            .strip()
        )

        if artist_name == search_name:
            matching_artists.append(artist)

    # If no exact matches, fallback
    if not matching_artists:
        matching_artists = artists

    # Rank artists
    best_score = -1

    for artist in matching_artists:

        score = 0

        disambiguation = (
            artist.get("disambiguation", "")
            .lower()
        )

        # Prefer actual bands
        if "band" in disambiguation:
            score += 10

        # Prefer metal / rock artists
        if "metal" in disambiguation:
            score += 8

        if "rock" in disambiguation:
            score += 5

        # Avoid engineers / aliases
        if "engineer" in disambiguation:
            score -= 10

        if "dj" in disambiguation:
            score -= 10

        if score > best_score:
            best_score = score
            best_artist = artist

    # Final fallback
    if not best_artist:
        best_artist = artists[0]
    
    mbid = best_artist.get("mbid")

    if not mbid:
        return [
            "No valid artist MBID found"
        ]
 

    # -----------------------------------
    # GET SETLISTS
    # -----------------------------------

    setlist_response = requests.get(
        "https://api.setlist.fm/rest/1.0/search/setlists",
        params={
            "artistMbid": mbid,
            "p": 1
        },
        headers=headers,
        timeout=15
    )

    if setlist_response.status_code == 429:
        return [
            "Rate limited by Setlist.fm. Try again shortly."
        ]

    if setlist_response.status_code != 200:
        return [
            "Could not fetch setlists"
        ]

    data = setlist_response.json()

    setlists = ensure_list(
        data.get("setlist")
    )





    counter = Counter()

    # -------------------------------
    # PARSE SONGS
    # -------------------------------


    valid_show_count = 0

    for show in setlists:

        # Skip malformed entries
        if not isinstance(show, dict):
            continue

        sets_container = show.get("sets")

        if not isinstance(sets_container, dict):
            continue

        sets = ensure_list(
            sets_container.get("set")
        )

        show_had_songs = False

        for st in sets:

            if not isinstance(st, dict):
                continue

            songs = ensure_list(
                st.get("song")
            )

            for song in songs:

                if not isinstance(song, dict):
                    continue

                name = song.get("name")

                if (
                    name and
                    isinstance(name, str)
                ):

                    counter[name] += 1
                    show_had_songs = True

        # Only count shows that actually had songs
        if show_had_songs:
            valid_show_count += 1

        # Stop after 5 VALID setlists
        if valid_show_count >= 5:
            break




        # --------------------------------
        # FALLBACK SEARCH
        # --------------------------------

        if not counter:

            for key, value in show.items():

                if key == "song":

                    songs = ensure_list(value)

                    for song in songs:

                        if isinstance(song, dict):

                            name = song.get("name")

                            if name:
                                counter[name] += 1

    songs = [
        name
        for name, count
        in counter.most_common(15)
    ]

    if not songs:
        songs = ["No recent songs found"]

    # -------------------------------
    # CACHE RESULTS
    # -------------------------------

    CACHE[cache_key] = songs

    return songs

# -----------------------------------
# RUN
# -----------------------------------

# pip install fastapi uvicorn requests
#
# SETLIST_API_KEY=Ub2-ndhLiZsRDqrNdoPjaRXZvjlmCZ8kl80j
#
# py -m uvicorn moshlist_full_stack_fastapi:app --reload