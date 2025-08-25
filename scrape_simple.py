#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

url = "https://animeadventures.fandom.com/wiki/Value_List"
headers = {"User-Agent": "Mozilla/5.0"}

logging.info("Fetching page...")
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

tables = soup.find_all("table")
logging.info(f"Found {len(tables)} tables")

all_data = []
for i, table in enumerate(tables):
    df = pd.read_html(str(table))[0]
    all_data.append(df)
    logging.info(f"Table {i+1}: {len(df)} rows")

# Save to Excel
output_file = "Anime_Adventures_Value_List_Fixed.xlsx"
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    for i, df in enumerate(all_data):
        sheet_name = f"Table_{i+1}"
        df.to_excel(writer, sheet_name=sheet_name, index=False)

logging.info(f"Saved to {output_file}")
print(f"Successfully created {output_file}")
