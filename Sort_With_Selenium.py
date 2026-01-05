import time
import os
import sys
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
    print("--- STARTING ROBUST SELENIUM SORT ---")
    
    # 1. SETUP CHROME with Desktop Resolution
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Force a large window so widgets render fully
    chrome_options.add_argument("--window-size=1920,1080")
    
    file_path = "file://" + os.path.abspath(INPUT_FILE)

    print(f"Loading {INPUT_FILE} in Headless Chrome...")
    driver = webdriver.Chrome(options=chrome_options)
    
    # Dictionary to store calculated sort scores
    # Key: Symbol, Value: (Quality + Technicals)
    stock_scores = {}

    try:
        driver.get(file_path)
        
        # 2. WAIT FOR DATA
        print("Waiting 20s for Trendlyne widgets to paint numbers...")
        try:
            # Wait until at least one percentage number appears
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "percent_number"))
            )
            # Add extra buffer for the rest to load
            time.sleep(10)
        except:
            print("WARNING: Timeout waiting for specific elements. Proceeding anyway.")

        # 3. SCRAPE
        rendered_cards = driver.find_elements(By.CSS_SELECTOR, ".card")
        print(f"Found {len(rendered_cards)} widgets. Extracting scores...")
        
        for card in rendered_cards:
            try:
                # A. Get Symbol (from the header we created)
                symbol_elem = card.find_element(By.CSS_SELECTOR, ".symbol")
                symbol_text = symbol_elem.text.strip()
                
                # B. Get Scores (Quality, Valuation, Technicals)
                # The widget usually renders 3 spans with class 'percent_number'
                score_elems = card.find_elements(By.CSS_SELECTOR, ".percent_number")
                
                q_score = 0.0
                t_score = 0.0
                
                if len(score_elems) >= 3:
                    # Index 0 = Quality
                    # Index 1 = Valuation
                    # Index 2 = Technicals
                    q_text = score_elems[0].text.strip().replace("/100", "")
                    t_text = score_elems[2].text.strip().replace("/100", "")
                    
                    q_score = float(q_text) if q_text else 0.0
                    t_score = float(t_text) if t_text else 0.0
                elif len(score_elems) >= 1:
                     # Fallback: If only 1 number loads, treat it as Quality
                    q_text = score_elems[0].text.strip().replace("/100", "")
                    q_score = float(q_text) if q_text else 0.0

                # C. Calculate Total Score (Quality + Technicals)
                total_score = q_score + t_score
                stock_scores[symbol_text] = total_score
                
                # DEBUG: Print the first 3 to verify we are getting data
                if len(stock_scores) <= 3:
                    print(f"DEBUG: {symbol_text} -> Q:{q_score} + T:{t_score} = {total_score}")

            except Exception:
                continue 

        print(f"Successfully captured scores for {len(stock_scores)} stocks.")
        
        if len(stock_scores) == 0:
            print("CRITICAL: No scores were captured. Sorting will fail.")

    except Exception as e:
        print(f"Browser Error: {e}")
    finally:
        driver.quit()

    # 4. RE-ORDER HTML
    print("Re-arranging the dashboard...")
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    
    grid_div = soup.find("div", class_="grid")
    if not grid_div:
        print("Error: No grid found.")
        return

    # Get raw cards
    original_cards = grid_div.find_all("div", class_="card", recursive=False)
    
    # Sort Function
    def get_sort_key(card_tag):
        sym_span = card_tag.find("span", class_="symbol")
        if sym_span:
            sym = sym_span.get_text().strip()
            # Default to -1 so stocks with no data drop to the bottom
            return stock_scores.get(sym, -1.0)
        return -1.0

    # Sort descending (Highest Score First)
    original_cards.sort(key=get_sort_key, reverse=True)
    
    # Apply changes
    grid_div.clear()
    for card in original_cards:
        grid_div.append(card)
        
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(str(soup))
        
    print("SUCCESS: Dashboard sorted by (Quality + Technicals).")

if __name__ == "__main__":
    main()
