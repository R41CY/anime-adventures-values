#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scrape_anime_adventures_by_section.py

Scrapes each section of the Anime Adventures Fandom Value List page
(Game Pass, Skins, Relics, Stats, S/A/B/C Tier) and outputs a single CSV.
"""

import csv
import requests
from bs4 import BeautifulSoup
import sys

BASE_URL = "https://animeadventures.fandom.com/wiki/Value_List"
SECTIONS = [
    "Game_Pass",
    "Skins",
    "Relics",
    "Stats",
    "S_Tier",
    "A_Tier",
    "B_Tier",
    "C_Tier"
]
OUTPUT_CSV = "all_sections_values.csv"

def fetch_section_table(section_id):
    """Fetch the HTML for a given section and return the first wikitable."""
    url = f"{BASE_URL}#{section_id}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    header = soup.find(id=section_id)
    if not header:
        sys.exit(f"Section '{section_id}' not found on page.")
    table = header.parent.find_next_sibling("table", class_="wikitable")
    if not table:
        sys.exit(f"No wikitable found after section '{section_id}'.")
    return table

def parse_table(table, section):
    """Parse a wikitable into list of dicts, adding 'section' key."""
    rows = table.find_all("tr")
    headers = [th.get_text(strip=True) for th in rows[0].find_all(["th","td"])]
    data = []
    for tr in rows[1:]:
        cols = [td.get_text(strip=True) for td in tr.find_all(["td","th"])]
        if len(cols) != len(headers):
            continue
        entry = dict(zip(headers, cols))
        entry["section"] = section
        data.append(entry)
    return data

def main():
    all_data = []
    for sec in SECTIONS:
        table = fetch_section_table(sec)
        section_data = parse_table(table, sec)
        all_data.extend(section_data)
        print(f"Fetched {len(section_data)} rows from {sec}")
    if not all_data:
        sys.exit("No data collected.")
    # Consolidate all unique headers across sections
    fieldnames = sorted({key for row in all_data for key in row.keys()})
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)
    print(f"Consolidated {len(all_data)} total rows into {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
