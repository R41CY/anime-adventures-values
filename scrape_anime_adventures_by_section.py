#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
improved_table_scraper.py
An improved scraper for Anime Adventures Value List that formats the data
in a more user-friendly way.
"""
import csv
import re
import requests
import time
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://animeadventures.fandom.com/wiki/Value_List"
OUTPUT_CSV = "anime_adventures_values_improved.csv"
EXCEL_OUTPUT = "anime_adventures_values.xlsx"

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
    
    # Try to identify tab headings
    tab_headings = []
    tab_elements = soup.select(".fandom-tabs-wrapper .fandom-tabs__tab") or soup.select("[class*='tab-navigation'] [class*='tab']")
    if tab_elements:
        for tab in tab_elements:
            tab_headings.append(tab.get_text(strip=True))
        print(f"Found tab headings: {tab_headings}")
    
    for i, table in enumerate(tables):
        # Assign a section name based on table position or tab heading
        section_name = tab_headings[i] if i < len(tab_headings) else f"Table {i+1}"
        
        # Look for a heading before the table
        prev = table.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
        if prev:
            heading = prev.get_text(strip=True)
            if heading:
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

def clean_and_format_data(data):
    """Clean and format the data for better readability"""
    cleaned_data = []
    
    # Identify key columns based on what we have
    for row in data:
        new_row = {"Section": row.get("Section", "Unknown")}
        
        # Clean up file names and extract character names
        for key, value in row.items():
            if key == "Section":
                continue
                
            # Handle file name and character name extraction
            if key.lower() in ["e", "d", "name"] and value.startswith("File:"):
                # Extract character name from file name pattern: File:Name.pngName
                file_match = re.match(r"File:(.*?)\.png(.*)", value)
                if file_match:
                    file_name, char_name = file_match.groups()
                    new_row["File Name"] = file_name
                    new_row["Character Name"] = char_name if char_name else file_name
                else:
                    new_row[key] = value
            # Handle values that are just character names (no file indicator)
            elif key.lower() in ["e", "d", "name"] and not value.startswith("File:"):
                new_row["Character Name"] = value
            # Add all other columns
            else:
                # Clean up column names
                clean_key = key
                if key in ["a", "b", "c", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o"]:
                    if key == "f" or key == "g":
                        clean_key = "Rarity"
                    elif key == "h" or key == "i":
                        clean_key = "Tier"
                    elif key == "j":
                        clean_key = "Status"
                    elif key == "l" or key == "m":
                        clean_key = "Value"
                new_row[clean_key] = value
        
        cleaned_data.append(new_row)
    
    return cleaned_data

def determine_categories(data):
    """Categorize items based on patterns"""
    categorized_data = []
    
    for row in data:
        new_row = row.copy()
        
        # Try to determine category based on file name, character name, or other fields
        character_name = row.get("Character Name", "")
        file_name = row.get("File Name", "")
        tier = row.get("Tier", "").upper()
        
        # Default category is the section name
        category = row.get("Section", "Unknown")
        
        # Map C-, C, B, A, S to categories
        if tier in ["S", "A", "B", "C", "C-"]:
            category = f"{tier} Tier"
        
        # Override with specific categories based on patterns
        if "Secret" in character_name or "Secret" in file_name:
            category = "Secret Units"
        elif "Star" in character_name or "Star" in file_name:
            category = "Star Units"
        elif any(keyword in character_name.lower() or keyword in file_name.lower() 
                 for keyword in ["relic", "artifact"]):
            category = "Relics"
        elif any(keyword in character_name.lower() or keyword in file_name.lower() 
                 for keyword in ["gamepass", "game pass"]):
            category = "Game Pass"
        
        new_row["Category"] = category
        categorized_data.append(new_row)
    
    return categorized_data

def save_to_csv(data, filename):
    """Save the extracted data to a CSV file"""
    if not data:
        print("No data to save")
        return False
        
    # Get all unique column names
    all_columns = set()
    for row in data:
        all_columns.update(row.keys())
    
    # Define a preferred column order
    preferred_columns = [
        "Section", "Category", "Character Name", "File Name", 
        "Rarity", "Tier", "Status", "Value"
    ]
    
    # Create the final column list
    fieldnames = []
    for col in preferred_columns:
        if col in all_columns:
            fieldnames.append(col)
            all_columns.discard(col)
    
    # Add any remaining columns
    fieldnames.extend(sorted(all_columns))
    
    # Write to CSV
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"Saved {len(data)} rows to {filename}")
    return True

def export_to_excel(data, filename):
    """Export data to Excel with formatting"""
    try:
        import pandas as pd
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(data)
        
        # Reorder columns if needed
        preferred_columns = [
            "Section", "Category", "Character Name", "File Name", 
            "Rarity", "Tier", "Status", "Value"
        ]
        
        cols = [col for col in preferred_columns if col in df.columns]
        other_cols = [col for col in df.columns if col not in preferred_columns]
        df = df[cols + other_cols]
        
        # Write to Excel
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Value List')
            
            # Access the worksheet
            workbook = writer.book
            worksheet = workbook['Value List']
            
            # Auto-adjust column width
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        print(f"Saved formatted Excel to {filename}")
        return True
    
    except ImportError:
        print("Pandas or openpyxl not available, skipping Excel export")
        return False

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
            return
        
        # Clean and format the data
        cleaned_data = clean_and_format_data(all_data)
        
        # Categorize items
        categorized_data = determine_categories(cleaned_data)
        
        # Save to CSV
        save_to_csv(categorized_data, OUTPUT_CSV)
        
        # Try to export to Excel if pandas is available
        try:
            export_to_excel(categorized_data, EXCEL_OUTPUT)
        except Exception as e:
            print(f"Excel export failed: {e}")
            print("To enable Excel export, install pandas and openpyxl:")
            print("pip install pandas openpyxl")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()