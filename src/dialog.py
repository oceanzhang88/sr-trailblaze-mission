# dialog.py

import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

from scraper import scrape_mission_hierarchy, scrape_page_content, download_audio_files, sanitize_filename
# --- MODIFIED: Re-import the HTML generator ---
from html_generator import generate_mission_html

WAIT_SECONDS = 15

def main():
    """
    Main function to scrape all Trailblaze missions and generate BOTH JSON and HTML files.
    """
    MAIN_MISSION_URL = "https://honkai-star-rail.fandom.com/wiki/Trailblaze_Mission"
    MASTER_FOLDER = "Trailblaze_Missions_Archive"

    try:
        print("--- Honkai: Star Rail Dialogue Scraper ---")
        
        os.makedirs(MASTER_FOLDER, exist_ok=True)
        print(f"All files will be saved in the '{MASTER_FOLDER}' directory.")

        mission_hierarchy = []

        print("\n[LOG] Initializing WebDriver...")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--log-level=3')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_page_load_timeout(WAIT_SECONDS)
        wait = WebDriverWait(driver, WAIT_SECONDS)
        print("[LOG] WebDriver initialized.")

        try:
            print(f"[LOG] Fetching main mission list from: {MAIN_MISSION_URL}")
            driver.get(MAIN_MISSION_URL)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#mw-content-text table.article-table")))
        except TimeoutException:
            print(f"\n[WARNING] The main mission page failed to load in {WAIT_SECONDS} seconds. Cannot continue.")

        print("[LOG] Mission list table located.")
        mission_hierarchy = scrape_mission_hierarchy(driver.page_source)
        
        if not mission_hierarchy:
            print("\n[FATAL] The scraper could not find any chapters or missions. The script cannot continue.")
            driver.quit()
            return
        
        # Save the mission hierarchy to a single JSON file for context
        hierarchy_filename = os.path.join(MASTER_FOLDER, 'mission_hierarchy.json')
        with open(hierarchy_filename, 'w', encoding='utf-8') as f:
            json.dump(mission_hierarchy, f, indent=4, ensure_ascii=False)
        print(f"\n[LOG] Saved mission hierarchy to '{hierarchy_filename}'")
        
        print(f"\n[LOG] Found {len(mission_hierarchy)} chapters. Starting individual mission scrape...")
        
        for chapter in mission_hierarchy:
            print(f"\n--- Processing Chapter: {chapter['chapter']} ---")
            for sub_chapter in chapter['sub_chapters']:
                print(f"  -- Sub-Group: {sub_chapter['title']} --")
                for mission in sub_chapter['missions']:
                    mission_title = mission['full_title']
                    mission_url = mission['url']
                    print(f"\n  Scraping Mission: {mission_title}")
                    
                    safe_mission_name = sanitize_filename(mission_title)
                    audio_folder_path = os.path.join(MASTER_FOLDER, f"{safe_mission_name}_audio")

                    # --- MODIFIED: Define filenames for both JSON and HTML ---
                    json_output_filename = os.path.join(MASTER_FOLDER, f"{safe_mission_name}.json")
                    html_output_filename = os.path.join(MASTER_FOLDER, f"{safe_mission_name}.html")
                    # This path is relative for use inside the HTML file's code
                    audio_folder_for_html = f"{safe_mission_name}_audio"
                    
                    try:
                        driver.get(mission_url)
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mw-parser-output")))
                    except TimeoutException:
                        print(f"    -> WARNING: Page load timed out for {mission_title}. Skipping.")
                        # continue

                    mission_html = driver.page_source
                    extracted_content = scrape_page_content(mission_html)

                    if not extracted_content:
                        print("    -> No dialogue content found on this page.")
                    else:
                        print(f"    -> Found dialogue items. Checking for audio...")
                        extracted_content = download_audio_files(extracted_content, audio_folder_path)
                        
                        # --- MODIFIED: Save as JSON file ---
                        with open(json_output_filename, 'w', encoding='utf-8') as f:
                            json.dump(extracted_content, f, indent=4, ensure_ascii=False)
                        print(f"    -> Successfully saved to '{json_output_filename}'")

                        # --- MODIFIED: Generate and save as HTML file ---
                        final_html = generate_mission_html(extracted_content, mission_title, audio_folder_for_html, mission_hierarchy, mission_url)
                        with open(html_output_filename, 'w', encoding='utf-8') as f:
                            f.write(final_html)
                        print(f"    -> Successfully saved to '{html_output_filename}'")
                    
        driver.quit()
        print("\n--- All missions processed successfully! ---")

    except Exception as e:
        print(f"\nAn unexpected error occurred in the main process: {e}")
        if 'driver' in locals() and driver:
            driver.quit()

if __name__ == '__main__':
    main()