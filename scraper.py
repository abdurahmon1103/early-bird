"""
Fetches a site's board page and extracts posts as a list of dicts
"""

import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin, quote

HEADERS = {
    # This makes us look like a normal browser to avoid block requests
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# If a site blocks GitHub Actions' IPs, set "use_proxy": true to route through MY_PROXY_URL
MY_PROXY_URL = os.environ.get("MY_PROXY_URL")

PROXY_URL_TEMPLATES = []
if MY_PROXY_URL:
    # Expected form: https://your-worker.your-subdomain.workers.dev/?url=
    PROXY_URL_TEMPLATES.append(MY_PROXY_URL.rstrip("/") + "?url={encoded_url}"
                                if not MY_PROXY_URL.rstrip().endswith("=")
                                else MY_PROXY_URL + "{encoded_url}")
PROXY_URL_TEMPLATES += [
    "https://api.allorigins.win/raw?url={encoded_url}",
    "https://corsproxy.io/?url={encoded_url}",
]

RETRIES_PER_PROXY = 2
RETRY_DELAY_SECONDS = 3


def fetch_posts(site_config: dict) -> list[dict]:
    name = site_config["name"]
    url = site_config["url"]
    use_proxy = site_config.get("use_proxy", False)

    response = _fetch_with_fallback(name, url, use_proxy)
    if response is None:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select(site_config["row_selector"])

    posts = []
    for row in rows:
        title_el = row.select_one(site_config["title_selector"])
        if title_el is None:
            continue

        date_selector = site_config.get("date_selector")
        if date_selector:
            date_el = row.select_one(date_selector)
            date_text = date_el.get_text(strip=True) if date_el else None
        else:
            date_text = None
            for td in row.select("td"):
                candidate = td.get_text(strip=True)
                if _try_parse_date(candidate, site_config["date_format"]) is not None:
                    date_text = candidate
                    break

        if date_text is None:
            # Row has a title but no parseable date anywhere --> skip
            continue

        title_text = title_el.get_text(strip=True)
        link = title_el.get("href", "")

        # Make relative links absolute (e.g. "board.php?..." -> full URL)
        if link and not link.startswith("http"):
            link = urljoin(site_config.get("base_url", url), link)

        parsed_date = _try_parse_date(date_text, site_config["date_format"])
        if parsed_date is None:
            continue

        posts.append({
            "title": title_text,
            "link": link,
            "post_date": parsed_date,
        })

    if not posts:
        print(f"[WARN] {name}: found 0 posts. Selectors in sites.json "
              f"probably need adjusting -- the site's HTML structure "
              f"may not match what's configured.")

    return posts


def _fetch_with_fallback(name: str, url: str, use_proxy: bool):
    if not use_proxy:
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            print(f"[WARN] Failed to fetch {name}: {e}")
            return None

    encoded_url = quote(url, safe="")

    for template in PROXY_URL_TEMPLATES:
        fetch_url = template.format(encoded_url=encoded_url)

        for attempt in range(1, RETRIES_PER_PROXY + 1):
            try:
                response = requests.get(fetch_url, headers=HEADERS, timeout=20)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                print(f"[WARN] {name}: proxy attempt {attempt} via "
                      f"{template.split('?')[0]} failed: {e}")
                if attempt < RETRIES_PER_PROXY:
                    time.sleep(RETRY_DELAY_SECONDS)

        print(f"[WARN] {name}: giving up on {template.split('?')[0]}, "
              f"trying next proxy if available.")

    print(f"[WARN] Failed to fetch {name}: all proxies exhausted.")
    return None


def _try_parse_date(date_text: str, date_format: str):
    # Returns a date object, or None if date_text isn't a real date
    try:
        return datetime.strptime(date_text, date_format).date()
    except ValueError:
        return None