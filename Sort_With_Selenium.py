import time
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# CONFIGURATION
INPUT_FILE = "index.html"
OUTPUT_FILE = "index.html"

def main():
    print("--- STARTING SMART SELENIUM SORT ---")
    
    # 1. SETUP CHROME
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    file_path = "file://" + os.path.abspath(INPUT_FILE)

    print("Launching Browser to fetch scores...")
    driver = webdriver.Chrome(options=chrome_options)
    
    # Dictionary to store scores: {'RELIANCE': 79.0, 'TCS': 65.0}
    stock_scores = {}

    try:
        # 2. OPEN PAGE & SCRAPE SCORES
        driver.get(file_path)
        
        # Wait for widgets to load (look for the percentage number)
        try:
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located((By.CLASS_NAME, "percent_number"))
            )
            time.sleep(5) # Extra buffer for all widgets to settle
        except:
            print("Warning: Timeout waiting for widgets. Proceeding with whatever loaded.")

        # Find all cards in the browser view
        rendered_cards = driver.find_elements(By.CSS_SELECTOR, ".card")
        
        print(f"Scraping scores from {len(rendered_cards)} loaded widgets...")
        
        for card in rendered_cards:
            try:
                # Extract Symbol
                symbol_elem = card.find_element(By.CSS_SELECTOR, ".symbol")
                symbol_text = symbol_elem.text.strip()
                
                # Extract Score (The first 'percent_number' is usually Quality)
                score_elems = card.find_elements(By.CSS_SELECTOR, ".percent_number")
                if score_elems:
                    raw_score = score_elems[0].text.strip().replace("/100", "")
                    score_val = float(raw_score)
                else:
                    score_val = 0.0
                
                stock_scores[symbol_text] = score_val
                
            except Exception:
                continue # Skip if a specific card fails

        print(f"Captured scores for {len(stock_scores)} stocks.")

    except Exception as e:
        print(f"Browser Error: {e}")
    finally:
        driver.quit()

    # 3. REARRANGE THE ORIGINAL FILE
    # Now we open the raw HTML file again (NOT the one from the browser)
    print("Re-ordering the original HTML file...")
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    
    # Find the container
    grid_div = soup.find("div", class_="grid")
    
    if not grid_div:
        print("Error: Could not find .grid div in HTML.")
        return

    # Find all card divs in the source HTML
    # Note: These are the "Raw" cards containing the widget scripts
    original_cards = grid_div.find_all("div", class_="card", recursive=False)
    
    # Helper function to get score for a raw card
    def get_sort_key(card_tag):
        # Find the symbol span inside this raw card
        sym_span = card_tag.find("span", class_="symbol")
        if sym_span:
            sym = sym_span.get_text().strip()
            # Return the score we scraped earlier (default to -1 if missing)
            return stock_scores.get(sym, -1.0)
        return -1.0

    # SORT: High score first
    original_cards.sort(key=get_sort_key, reverse=True)
    
    # 4. SAVE
    # Clear the current grid and re-attach sorted cards
    grid_div.clear()
    for card in original_cards:
        grid_div.append(card)
        
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(str(soup))
        
    print(f"SUCCESS: Re-ordered {len(original_cards)} stocks based on fetched scores.")

if __name__ == "__main__":
    main()
