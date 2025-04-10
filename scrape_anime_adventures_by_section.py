#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simple_table_scraper.py
A simplified version that directly extracts all tables from the Anime Adventures
Value List page without trying to handle tab navigation.
"""
import csv
import requests
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://animeadventures.fandom.com/wiki/Value_List"
OUTPUT_CSV = "anime_adventures_values.csv"

def get_page_with_selenium():
    """Use Selenium to load the page with JavaScript execution"""
    print("Launching Chrome to fetch dynamic content...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        driver.get(BASE_URL)
        print("Waiting for page to load completely...")
        time.sleep(5)  # Give time for JavaScript to execute
        
        # Print page title to verify we're on the right page
        print(f"Page title: {driver.title}")
        
        # Wait for tables to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        
        html = driver.page_source
        print(f"HTML length: {len(html)} characters")
        return html
    finally:
        driver.quit()

def extract_all_tables(html):
    """Extract all tables from the HTML"""
    soup = BeautifulSoup(html, "html.parser")
    all_data = []
    
    # Find all tables
    tables = soup.find_all("table")
    print(f"Found {len(tables)} tables on the page")
    
    for i, table in enumerate(tables):
        # Assign a section name based on table position
        section_name = f"Table {i+1}"
        
        # Look for a heading before the table
        heading = None
        prev = table.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
        if prev:
            heading = prev.get_text(strip=True)
            section_name = heading
        
        # Extract rows
        rows = table.find_all("tr")
        if len(rows) < 2:
            print(f"Skipping {section_name} - not enough rows")
            continue
        
        # Extract headers from first row
        header_cells = rows[0].find_all(["th", "td"])
        headers = []
        for cell in header_cells:
            header_text = cell.get_text(strip=True)
            if not header_text:
                header_text = f"Column{len(headers)+1}"
            headers.append(header_text)
        
        print(f"Table {i+1} headers: {headers}")
        
        # Extract data rows
        table_data = []
        for row_idx, row in enumerate(rows[1:], 1):
            cells = row.find_all(["td", "th"])
            row_data = {}
            
            # Skip rows with different cell count
            if len(cells) != len(headers):
                print(f"  Skipping row {row_idx} in {section_name} - cell count mismatch")
                continue
                
            # Process each cell
            for j, cell in enumerate(cells):
                # Handle images - extract alt text or filename
                img = cell.find("img")
                if img and not cell.get_text(strip=True):
                    value = img.get("alt", "") or img.get("src", "").split("/")[-1]
                else:
                    value = cell.get_text(strip=True)
                    
                row_data[headers[j]] = value
            
            # Add the section name
            row_data["Section"] = section_name
            table_data.append(row_data)
        
        print(f"Extracted {len(table_data)} rows from {section_name}")
        all_data.extend(table_data)
    
    return all_data

def save_to_csv(data, filename):
    """Save the extracted data to a CSV file"""
    if not data:
        print("No data to save")
        return False
        
    # Get all unique column names
    all_columns = set()
    for row in data:
        all_columns.update(row.keys())
    
    # Make sure "Section" is the first column
    if "Section" in all_columns:
        all_columns.remove("Section")
        fieldnames = ["Section"] + sorted(all_columns)
    else:
        fieldnames = sorted(all_columns)
    
    # Write to CSV
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"Saved {len(data)} rows to {filename}")
    return True

def main():
    try:
        # Get the page content
        html = get_page_with_selenium()
        
        # Extract table data
        all_data = extract_all_tables(html)
        
        if not all_data:
            print("\nNo data extracted. Saving the HTML for inspection...")
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("HTML saved to debug_page.html")
            
            # Print a sample of the HTML for more context
            soup = BeautifulSoup(html, "html.parser")
            print("\nFirst 1000 characters of the HTML body:")
            body = soup.find("body")
            if body:
                print(str(body)[:1000])
            return
        
        # Save to CSV
        save_to_csv(all_data, OUTPUT_CSV)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()