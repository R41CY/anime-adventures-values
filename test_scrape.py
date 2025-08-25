#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

url = "https://animeadventures.fandom.com/wiki/Value_List"

# Try to fetch the page with requests
response = requests.get(url)
print(f"Status code: {response.status_code}")
print(f"Response length: {len(response.text)}")

# Parse with BeautifulSoup
soup = BeautifulSoup(response.text, 'html.parser')

# Look for tables
tables = soup.find_all('table')
print(f"Found {len(tables)} tables")

# Save the HTML to check
with open("test_page.html", "w", encoding="utf-8") as f:
    f.write(response.text)
print("Saved page to test_page.html")

# Look for any indicators that JavaScript is needed
if "Enable JavaScript" in response.text or "requires JavaScript" in response.text:
    print("Warning: This page might require JavaScript to display content")