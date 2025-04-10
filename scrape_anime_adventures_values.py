#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scrape_anime_adventures_values.py

Scrapes Anime Adventures Fandom 'Value List' tables and consolidates all items into one CSV.
"""

import csv
import requests
from bs4 import BeautifulSoup
import sys

FANDOM_URL = "https://anime-adventures.fandom.com/wiki/Value_List"
OUTPUT_CSV = "all_tradeable_values.csv"

def fetch_html(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        sys.exit(f"Failed to fetch HTML: {e}")

def parse_value_tables(html: str):
    soup = BeautifulSoup(html, "html.parser")
    section = soup.find(id="Value_List")
    if not section:
        sys.exit("Cannot find 'Value List' section.")
    data = []
    node = section.parent.find_next_sibling()
    while node and node.name != "h2":
        if node.name == "h3":
            category = node.get_text(strip=True)
        if node.name == "table" and "wikitable" in node.get("class", []):
            headers = [th.get_text(strip=True) for th in node.find_all("tr")[0].find_all("th")]
            try:
                idx_value = headers.index("Value")
            except ValueError:
                idx_value = None
            for row in node.find_all("tr")[1:]:
                cols = [td.get_text(strip=True) for td in row.find_all(["td","th"])]
                if idx_value is not None and idx_value < len(cols):
                    data.append({
                        "category": category,
                        "name": cols[0],
                        "value": cols[idx_value]
                    })
        node = node.find_next_sibling()
    return data

def write_csv(data):
    if not data:
        sys.exit("No data to write.")
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category","name","value"])
        writer.writeheader()
        writer.writerows(data)
    print(f"Wrote {len(data)} records to {OUTPUT_CSV}")

if __name__ == "__main__":
    html = fetch_html(FANDOM_URL)
    data = parse_value_tables(html)
    write_csv(data)
