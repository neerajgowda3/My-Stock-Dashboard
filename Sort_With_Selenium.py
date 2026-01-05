import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# CONFIGURATION
INPUT_FILE = "index.html"
OUTPUT_FILE = "index.html"

def get_score_from_card(card_element):
    """
    Finds the Quality Score inside a single rendered card.
    Based on your screenshot, the score is in <span class="percent_number">79</span>.
    Usually the first one is Quality.
    """
    try:
        # We look for all scores (Quality, Valuation, Technicals)
        # Your screenshot shows they are all 'span.percent_number'
        scores = card_element.find_elements(By.CSS_SELECTOR, ".percent_number")
        
        if len(scores) > 0:
            # The first number is usually Quality. 
            # We strip whitespace and "/100" if present.
            raw_text = scores[0].text.strip().replace("/100", "")
            return float(raw_text) if raw_text else 0
        return 0
    except:
        return 0

def main():
    print("--- STARTING SELENIUM SORTER ---")
    
    # 1. SETUP CHROME (HEADLESS)
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Important: Load local file path properly
    import os
    file_path = "file://" + os.path.abspath(INPUT_FILE)

    print("Launching Browser...")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # 2. OPEN THE FILE
        print(f"Loading {file_path}...")
        driver.get(file_path)

        # 3. WAIT FOR WIDGETS (CRITICAL STEP)
        print("Waiting for widgets to render (this may take time)...")
        # Wait up to 20 seconds for at least one '.percent_number' to appear
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "percent_number"))
            )
            # Give it a few extra seconds for ALL 500 to finish
            time.sleep(10) 
        except:
            print("WARNING: Timeout waiting for widgets. They might be slow or blocked.")

        # 4. SCRAPE & SORT
        print("Scraping scores from the live page...")
        
        # Find all our custom .card containers
        cards = driver.find_elements(By.CSS_SELECTOR, ".card")
        
        card_data = []
        for card in cards:
            score = get_score_from_card(card)
            # We grab the 'outerHTML' which is the fully rendered HTML of that card
            html_content = card.get_attribute('outerHTML')
            card_data.append({'html': html_content, 'score': score})

        print(f"Scraped {len(card_data)} cards. Sorting...")
        
        # Sort by Score (Descending)
        card_data.sort(key=lambda x: x['score'], reverse=True)

        # 5. REBUILD HTML
        # We need the original header/footer, so we read the raw file again
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
        
        # clear the current grid
        grid_div = soup.find("div", class_="grid")
        if grid_div:
            grid_div.clear()
            # Inject our new sorted HTML
            # Note: We are injecting the *rendered* HTML from Selenium, 
            # which might include the expanded widget code.
            # This makes the file static (snapshots the data) which is actually good.
            for item in card_data:
                # Parse the selenium HTML string back into a soup object
                card_soup = BeautifulSoup(item['html'], "html.parser")
                grid_div.append(card_soup)
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(str(soup))
            
        print("SUCCESS: HTML sorted and saved.")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        exit(1)
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
