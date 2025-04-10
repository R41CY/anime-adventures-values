#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scrape_tabbed_sections.py

Scrapes each 'cfx-tab cfx-tab-content' <div> from the Anime Adventures
Fandom Value List page. It pulls the table under each tab
(Game Pass, Skins, Relics, Stats, etc.) and consolidates them into one CSV.
"""

import csv
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://animeadventures.fandom.com/wiki/Value_List"
SECTIONS = [
    "Game Pass",
    "Skins",
    "Relics",
    "Stats",
    "S Tier",
    "A Tier",
    "B Tier",
    "C Tier"
]
OUTPUT_CSV = "tabbed_values.csv"

def fetch_html(url):
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.text

def parse_tab_div(div):
    """
    Given a <div class="cfx-tab cfx-tab-content" data-subtab="Game Pass">, etc.
    find the <table> and parse rows. Returns a list of dicts.
    """
    table = div.find("table", class_="wikitable")
    if not table:
        return []

    rows = table.find_all("tr")
    if len(rows) < 2:
        return []  # no data rows

    # Extract headers from the first row
    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th","td"])]
    data = []
    for tr in rows[1:]:
        cols = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
        # Only parse rows with matching column count
        if len(cols) == len(headers):
            entry = dict(zip(headers, cols))
            data.append(entry)
    return data

def main():
    html = fetch_html(BASE_URL)
    soup = BeautifulSoup(html, "html.parser")

    # Each tab content is something like:
    # <div class="cfx-tab cfx-tab-content" data-subtab="Game Pass"> ... table ... </div>
    tab_divs = soup.find_all("div", class_="cfx-tab cfx-tab-content")

    all_data = []
    for div in tab_divs:
        subtab_name = div.get("data-subtab", "").strip()
        # If you only want certain tabs, filter them with your SECTIONS list:
        if subtab_name in SECTIONS:
            rows = parse_tab_div(div)
            # Append each row to the master list, tagging it with the subtab name
            for row in rows:
                row["section"] = subtab_name
            all_data.extend(rows)
            print(f"Found {len(rows)} rows under '{subtab_name}' tab.")

    if not all_data:
        print("No data extracted. Possibly the structure is different, or the tabs are dynamic.")
        return

    # Collect all column names (headers + 'section')
    fieldnames = sorted({col for row in all_data for col in row.keys()})

    # Write to CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)

    print(f"Wrote {len(all_data)} total rows to '{OUTPUT_CSV}'.")

if __name__ == "__main__":
    main()
