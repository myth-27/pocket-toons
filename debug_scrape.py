import requests
import os

url = "https://www.webtoons.com/en/fantasy/tower-of-god/season-3-ep-235-season-3-finale/viewer?title_no=95&episode_no=653"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.webtoons.com/"
}

try:
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    with open("webtoon_debug.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"Saved {len(response.text)} characters to webtoon_debug.html")
except Exception as e:
    print(f"Error: {e}")
