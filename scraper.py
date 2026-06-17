import requests
from bs4 import BeautifulSoup
from dateutil import parser

# 1. Define your venues and their specific HTML blueprints
venues = [
    {
        "name": "Baltimore Soundstage",
        "url": "https://www.baltimoresoundstage.com/calendar/",
        "container": "article.event",
        "selectors": {
            "title": ".title",
            "date": ".event-date",
            "support": ".supporting-acts",
            "time": ".event-time",
            "ticket": "a.btn-green"
        }
    },
    {
        "name": "Nevermore Hall",
        "url": "https://nevermorehall.com/events/",
        "container": ".post_content_wrap",
        "selectors": {
            "title": ".entry-title",
            "date": ".post_date",
            "support": ".event-attractions-list",
            "time": ".event_timing",
            "ticket": ".ticket-button"
        }
    }
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
all_shows = []

# 2. Scrape the data from both sites
for venue in venues:
    try:
        response = requests.get(venue['url'], headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        events = soup.select(venue['container'])
        
        for event in events:
            sel = venue['selectors']
            
            title = event.select_one(sel['title']).get_text(strip=True) if event.select_one(sel['title']) else "Unknown Artist"
            date_str = event.select_one(sel['date']).get_text(strip=True) if event.select_one(sel['date']) else "TBD"
            support = event.select_one(sel['support']).get_text(strip=True) if event.select_one(sel['support']) else "None"
            time_val = event.select_one(sel['time']).get_text(strip=True) if event.select_one(sel['time']) else ""
            
            t_link = event.select_one(sel['ticket'])
            ticket_url = t_link['href'] if t_link and t_link.has_attr('href') else "#"

            try:
                clean_date = parser.parse(date_str, fuzzy=True)
            except:
                clean_date = parser.parse("2026-12-31")

            all_shows.append({
                "venue": venue['name'],
                "date_obj": clean_date,
                "date_str": date_str,
                "title": title,
                "support": support,
                "time": time_val,
                "ticket": ticket_url
            })
    except Exception as e:
        print(f"Error scraping {venue['name']}: {e}")

# 3. Sort chronologically
all_shows.sort(key=lambda x: x['date_obj'])

# 1. Read your existing designed page
with open("index.html", "r", encoding="utf-8") as f:
    existing_html = f.read()

# 2. Build the live show blocks matching your exact HTML framework
cards_html = ""
for show in all_shows:
    # Extract uppercase 3-letter month (e.g., "MAY") and day number (e.g., "24")
    month_str = show['date_obj'].strftime('%b').upper()
    day_str = show['date_obj'].strftime('%d')
    
    # Format support acts line if they exist
    artist_display = f"{show['title']}"
    if show['support'] and show['support'] != "None":
        artist_display += f" <span style='font-size: 0.85em; font-weight: normal; color: #888;'>w/ {show['support']}</span>"

    cards_html += f"""    <div class='panel'>
    <div class='show'>
        <div class='date'>
            <div class='m'>{month_str}</div>
            <div class='d'>{day_str}</div>
        </div>
        <div>
            <strong>{artist_display}</strong>
            <div class='meta'>{show['venue']}</div>
        </div>
        <a class='btn' href='{show['ticket']}' target='_blank'>Tickets</a>
    </div></div>\n"""

# 3. Splice the new blocks between your two text markers
import re
pattern = r"Upcoming Shows</h2>.*?<div id='playlists'>"
replacement = f"Upcoming Shows</h2>\n{cards_html}\n<div id='playlists'>"

# Replace the placeholder area with your beautifully structured list
updated_html = re.sub(pattern, replacement, existing_html, flags=re.DOTALL)

# 4. Save it back to index.html
with open("index.html", "w", encoding="utf-8") as f:
    f.write(updated_html)

print("Successfully spliced structured concert data into your custom layout!")
