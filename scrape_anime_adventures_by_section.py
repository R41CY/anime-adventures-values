#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anime_adventures_excel_report.py
Creates a professionally formatted Excel report from the Anime Adventures Value List
with color coding, multiple sheets, and proper organization.
"""
import csv
import re
import requests
import time
import os
import glob
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Make sure these packages are installed:
# pip install pandas openpyxl xlsxwriter

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment, Color
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.formatting.rule import Rule
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

BASE_URL = "https://animeadventures.fandom.com/wiki/Value_List"
OUTPUT_EXCEL_PATTERN = "Anime_Adventures_Value_List{}.xlsx"

def get_next_file_number():
    """Find the next available file number by checking existing files"""
    existing_files = glob.glob("Anime_Adventures_Value_List*.xlsx")
    if not existing_files:
        return 1
    
    # Extract numbers from existing filenames
    numbers = []
    pattern = re.compile(r"Anime_Adventures_Value_List(\d+)\.xlsx")
    for filename in existing_files:
        match = pattern.match(filename)
        if match:
            numbers.append(int(match.group(1)))
    
    # Return the next number in sequence
    return max(numbers) + 1 if numbers else 1

# Define color schemes for categories
COLOR_SCHEMES = {
    "S Tier": {"header": "1F4E78", "cell": "D6E5F3"},
    "A Tier": {"header": "375623", "cell": "E2EFDA"},
    "B Tier": {"header": "833C0B", "cell": "FFF2CC"},
    "C Tier": {"header": "7030A0", "cell": "E4D2F2"},
    "C- Tier": {"header": "7030A0", "cell": "E4D2F2"},
    "Secret Units": {"header": "C00000", "cell": "FFCCCC"},
    "Game Pass": {"header": "FFC000", "cell": "FFF2CC"},
    "Relics": {"header": "4472C4", "cell": "D6E5F3"},
    "Default": {"header": "404040", "cell": "F2F2F2"}
}

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
    """Clean and format the data for better readability and organization"""
    cleaned_data = []
    
    for row in data:
        new_row = {"Section": row.get("Section", "Unknown")}
        
        # Handle non-standard column names
        for key, value in row.items():
            if key == "Section":
                continue
                
            # Process file names and character names
            if key.lower() in ["e", "d", "name"] and "File:" in value:
                # Extract character name from file name: File:Name.png
                file_match = re.match(r".*?File:(.*?)\.png(.*)", value)
                if file_match:
                    file_name, char_name = file_match.groups()
                    new_row["File Name"] = file_name.strip()
                    # Use char_name if available, otherwise use file_name but without duplication
                    if char_name and char_name.strip():
                        new_row["Character Name"] = char_name.strip()
                    else:
                        new_row["Character Name"] = file_name.strip()
                else:
                    new_row[key] = value
            # Handle values that are just character names (no file indicator)
            elif key.lower() in ["e", "d", "name"] and "File:" not in value:
                # Remove any duplicate prefixes like "ShinyShiny"
                clean_value = re.sub(r"(\w+)\1", r"\1", value)
                new_row["Character Name"] = clean_value
            # Add other columns with better names
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
                    elif key == "a" or key == "b" or key == "c":
                        clean_key = "Quantity"
                new_row[clean_key] = value
        
        # Additional cleanup for character names to remove duplicate prefixes
        if "Character Name" in new_row:
            char_name = new_row["Character Name"]
            # Fix duplicate word patterns like "ShinyShiny"
            new_row["Character Name"] = re.sub(r"(\b\w+)(\1\b)", r"\1", char_name)
        
        cleaned_data.append(new_row)
    
    return cleaned_data

def determine_categories(data):
    """Categorize items based on patterns and data"""
    categorized_data = []
    
    for row in data:
        new_row = row.copy()
        
        # Try to determine category based on file name, character name, or other fields
        character_name = row.get("Character Name", "")
        file_name = row.get("File Name", "")
        tier = row.get("Tier", "").upper()
        status = row.get("Status", "").lower()
        
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
        
        # Try to determine rarity if not already set
        if "Rarity" not in new_row:
            if tier == "S":
                new_row["Rarity"] = "Legendary"
            elif tier == "A":
                new_row["Rarity"] = "Epic"
            elif tier == "B":
                new_row["Rarity"] = "Rare"
            elif tier in ["C", "C-"]:
                new_row["Rarity"] = "Common"
        
        # Set stability if not already there
        if "Status" not in new_row and "stable" in status:
            new_row["Status"] = "Stable"
        
        new_row["Category"] = category
        categorized_data.append(new_row)
    
    return categorized_data

def remove_duplicate_prefixes(data):
    """Remove any duplicate prefixes like 'ShinyShiny' from character names"""
    for row in data:
        if "Character Name" in row:
            # Fix repeating words like "ShinyShiny"
            char_name = row["Character Name"]
            # First, handle specific pattern for "ShinyShiny"
            char_name = re.sub(r"ShinyShiny", "Shiny", char_name)
            # Then handle any other duplicate word pattern
            char_name = re.sub(r"(\b\w+)\s+\1\b", r"\1", char_name)
            # Update the name
            row["Character Name"] = char_name
    return data

def create_excel_report(data, filename):
    """Create a professionally formatted Excel report"""
    if not data:
        print("No data to export")
        return False
    
    print(f"Creating Excel report: {filename}")
    
    # Group data by category
    categories = {}
    for row in data:
        category = row.get("Category", "Other")
        if category not in categories:
            categories[category] = []
        categories[category].append(row)
    
    # Create a pandas Excel writer using XlsxWriter as the engine
    writer = pd.ExcelWriter(filename, engine='xlsxwriter')
    
    # Create a DataFrame from all data for the overview sheet
    df_all = pd.DataFrame(data)
    
    # Reorder columns logically
    preferred_columns = [
        "Character Name", "File Name", "Category", "Tier", "Rarity", 
        "Status", "Value", "Quantity", "Section"
    ]
    
    # Ensure all columns exist (fill with empty strings if not)
    for col in preferred_columns:
        if col not in df_all.columns:
            df_all[col] = ""
    
    # Get remaining columns
    other_columns = [col for col in df_all.columns if col not in preferred_columns]
    
    # Create final column order
    column_order = preferred_columns + other_columns
    
    # Reorder DataFrame columns
    df_all = df_all[column_order]
    
    # Create the overview sheet with all data
    df_all.to_excel(writer, sheet_name='Overview', index=False)
    
    # Get workbook and add a overview worksheet
    workbook = writer.book
    
    # Format for header cells
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#D9D9D9',
        'border': 1,
        'font_size': 12
    })
    
    # Format for category header cells
    category_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'fg_color': '#4472C4',
        'font_color': 'white',
        'border': 1,
        'font_size': 14
    })
    
    # Overview worksheet formatting
    overview_sheet = writer.sheets['Overview']
    overview_sheet.freeze_panes(1, 0)  # Freeze the header row
    
    # Set column widths
    for i, col in enumerate(df_all.columns):
        # Calculate column width based on column name and max content length
        max_len = df_all[col].astype(str).map(len).max()
        col_len = max(max_len, len(col)) + 3  # Add some padding
        overview_sheet.set_column(i, i, col_len)
    
    # Add header formatting
    for col_num, value in enumerate(df_all.columns.values):
        overview_sheet.write(0, col_num, value, header_format)
    
    # Add category-specific sheets
    for category, category_data in categories.items():
        if not category_data:
            continue
        
        # Create safe sheet name (max 31 chars, no special chars)
        sheet_name = re.sub(r'[\\/*\[\]:?]', '', category)[:31]
        
        # Create DataFrame for this category
        df_category = pd.DataFrame(category_data)
        
        # Reorder columns the same way
        for col in preferred_columns:
            if col not in df_category.columns:
                df_category[col] = ""
        
        # Get other columns that might be specific to this category
        cat_other_columns = [col for col in df_category.columns if col not in preferred_columns]
        
        # Create final column order for this category
        cat_column_order = preferred_columns + cat_other_columns
        
        # Reorder DataFrame columns
        df_category = df_category[cat_column_order]
        
        # Add data to the sheet
        df_category.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Format the category sheet
        category_sheet = writer.sheets[sheet_name]
        category_sheet.freeze_panes(1, 0)  # Freeze the header row
        
        # Get the color scheme for this category
        color_scheme = COLOR_SCHEMES.get(category, COLOR_SCHEMES["Default"])
        
        # Create category-specific header format
        cat_header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#' + color_scheme["header"],
            'font_color': 'white',
            'border': 1,
            'font_size': 12
        })
        
        # Create category-specific cell format
        cat_cell_format = workbook.add_format({
            'border': 1,
            'fg_color': '#' + color_scheme["cell"],
        })
        
        # Apply formatting to the header row
        for col_num, value in enumerate(df_category.columns.values):
            category_sheet.write(0, col_num, value, cat_header_format)
        
        # Set column widths
        for i, col in enumerate(df_category.columns):
            max_len = df_category[col].astype(str).map(len).max()
            col_len = max(max_len, len(col)) + 3
            category_sheet.set_column(i, i, col_len)
        
        # Apply alternating row colors
        row_count = len(df_category) + 1  # +1 for header
        category_sheet.add_table(0, 0, row_count-1, len(df_category.columns)-1, {
            'columns': [{'header': col} for col in df_category.columns],
            'style': 'Table Style Medium 2',
            'first_column': True
        })
    
    # Create a Summary sheet
    summary_data = []
    for category, category_data in categories.items():
        summary_data.append({
            'Category': category,
            'Count': len(category_data),
            'Average Value': sum(float(row.get('Value', 0)) for row in category_data if row.get('Value', '').isdigit()) / len(category_data) if category_data else 0
        })
    
    # Sort by count descending
    summary_data.sort(key=lambda x: x['Count'], reverse=True)
    
    # Create summary DataFrame
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(writer, sheet_name='Summary', index=False)
    
    # Format the summary sheet
    summary_sheet = writer.sheets['Summary']
    
    # Apply formatting to the summary sheet
    for col_num, value in enumerate(df_summary.columns.values):
        summary_sheet.write(0, col_num, value, header_format)
    
    # Set column widths
    summary_sheet.set_column(0, 0, 20)  # Category
    summary_sheet.set_column(1, 1, 10)  # Count
    summary_sheet.set_column(2, 2, 15)  # Average Value
    
    # Add a chart
    chart = workbook.add_chart({'type': 'column'})
    
    # Configure the chart
    chart.add_series({
        'name': 'Item Count',
        'categories': ['Summary', 1, 0, len(summary_data), 0],
        'values': ['Summary', 1, 1, len(summary_data), 1],
    })
    
    chart.set_title({'name': 'Items by Category'})
    chart.set_x_axis({'name': 'Category'})
    chart.set_y_axis({'name': 'Count'})
    
    # Insert the chart into the worksheet
    summary_sheet.insert_chart('E2', chart, {'x_scale': 1.5, 'y_scale': 1.5})
    
    # Close the writer
    writer.close()
    
    print(f"Excel report created successfully: {filename}")
    return True

def main():
    try:
        # Get the next available file number
        next_file_number = get_next_file_number()
        output_excel = OUTPUT_EXCEL_PATTERN.format(next_file_number)
        print(f"Using file name: {output_excel}")
        
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
        
        # Apply additional cleaning to remove duplicate prefixes
        final_data = remove_duplicate_prefixes(categorized_data)
        
        # Create Excel report
        try:
            create_excel_report(final_data, output_excel)
        except Exception as e:
            print(f"Excel report creation failed: {e}")
            print("Make sure you have required packages installed:")
            print("pip install pandas openpyxl xlsxwriter")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()