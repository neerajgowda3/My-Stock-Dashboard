import time
import os
import json
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
INPUT_FILE = "index.html"
OUTPUT_FILE = "index.html"
HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_history(data):
    # Only save if we actually found data to avoid wiping history with zeros
    if len(data) > 0:
        with open(HISTORY_FILE, "w") as f:
            json.dump(data, f)

def get_diff_html(current, previous):
    if previous is None or current == 0: return ""
    diff = current - previous
    if diff > 0:
        return f'<span style="color:#28a745; font-size:11px; font-weight:bold; margin-left:2px;">▲{int(diff)}</span>'
    elif diff < 0:
        return f'<span style="color:#dc3545; font-size:11px; font-weight:bold; margin-left:2px;">▼{int(abs(diff))}</span>'
    return ""

def main():
    print("--- STARTING: SCRAPE, SORT & TRACK ---")
    
    # 1. SETUP CHROME (Stealth Mode)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Fake User-Agent to look less like a robot
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    file_path = "file://" + os.path.abspath(INPUT_FILE)
    driver = webdriver.Chrome(options=chrome_options)

    current_data = {} # Will store {'RELIANCE': {'q': 55, 'v': 40, 't': 60}}

    try:
        print("Loading page...")
        driver.get(file_path)
        
        # 2. WAIT FOR WIDGETS
        print("Waiting for scores to render...")
        try:
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located((By.CLASS_NAME, "percent_number"))
            )
            time.sleep(5) 
        except:
            print("Warning: Widgets took too long. Proceeding...")

        # 3. SCRAPE SCORES
        cards = driver.find_elements(By.CSS_SELECTOR, ".card")
        print(f"Scraping {len(cards)} cards...")
        
        for card in cards:
            try:
                sym = card.find_element(By.CSS_SELECTOR, ".symbol").text.strip()
                
                # Find all 3 numbers (Quality, Valuation, Technicals)
                nums = card.find_elements(By.CSS_SELECTOR, ".percent_number")
                
                q, v, t = 0.0, 0.0, 0.0
                if len(nums) >= 3:
                    q = float(nums[0].text.strip().replace("/100","") or 0)
                    v = float(nums[1].text.strip().replace("/100","") or 0)
                    t = float(nums[2].text.strip().replace("/100","") or 0)
                elif len(nums) >= 1:
                    q = float(nums[0].text.strip().replace("/100","") or 0)

                current_data[sym] = {'q': q, 'v': v, 't': t}
                
            except:
                continue
                
        print(f"Captured data for {len(current_data)} stocks.")

    except Exception as e:
        print(f"Browser Error: {e}")
    finally:
        driver.quit()

    # 4. COMPARE & UPDATE HTML
    print("Comparing with history and updating HTML...")
    
    history = load_history()
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    
    grid = soup.find("div", class_="grid")
    if not grid: return

    # We process the raw HTML cards now
    raw_cards = grid.find_all("div", class_="card", recursive=False)
    
    # Store cards with their sorting score to sort later
    cards_with_scores = []

    for card in raw_cards:
        # Find symbol in the raw HTML
        sym_tag = card.find("span", class_="symbol")
        if not sym_tag: continue
        
        sym = sym_tag.get_text().strip()
        
        # Get Scores (Current & History)
        curr = current_data.get(sym, {'q':0,'v':0,'t':0})
        hist = history.get(sym, {})
        
        # Calculate Diff Badges
        q_badge = get_diff_html(curr['q'], hist.get('q'))
        v_badge = get_diff_html(curr['v'], hist.get('v'))
        t_badge = get_diff_html(curr['t'], hist.get('t'))
        
        # --- INSERT SCORE BOARD INTO CARD ---
        # We check if a scoreboard already exists (to update it) or create new
        score_row = card.find("div", class_="custom-score-row")
        if score_row:
            score_row.decompose() # Remove old one to rebuild fresh
            
        new_row = soup.new_tag("div", **{"class": "custom-score-row"})
        new_row['style'] = "display:flex; justify-content:space-around; background:#f9f9f9; padding:5px; font-size:12px; border-bottom:1px solid #eee;"
        
        # Helper to create score column
        def create_col(label, val, badge):
            div = soup.new_tag("div", style="text-align:center;")
            div.innerHTML = f"<div style='color:#666; font-size:10px;'>{label}</div><div style='font-weight:bold;'>{int(val)}{badge}</div>"
            # BS4 doesn't support innerHTML directly for simple strings with tags, so we append:
            lbl = soup.new_tag("div", style="color:#666; font-size:10px;")
            lbl.string = label
            v_cont = soup.new_tag("div", style="font-weight:bold;")
            v_cont.append(str(int(val)))
            if badge:
                # badge is HTML string, parse it
                b_soup = BeautifulSoup(badge, "html.parser")
                v_cont.append(b_soup)
            div.append(lbl)
            div.append(v_cont)
            return div

        new_row.append(create_col("Qual", curr['q'], q_badge))
        new_row.append(create_col("Val", curr['v'], v_badge))
        new_row.append(create_col("Tech", curr['t'], t_badge))
        
        # Insert after header
        header = card.find("div", class_="card-header")
        if header:
            header.insert_after(new_row)
            
        # Add to list for sorting
        # Sort Score = Quality + Technicals
        sort_score = curr['q'] + curr['t']
        cards_with_scores.append((sort_score, card))

    # 5. SORT
    print("Sorting...")
    cards_with_scores.sort(key=lambda x: x[0], reverse=True)
    
    # 6. SAVE HTML
    grid.clear()
    for score, card in cards_with_scores:
        grid.append(card)
        
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(str(soup))
        
    # 7. SAVE HISTORY
    save_history(current_data)
    print("SUCCESS: Dashboard updated and history saved.")

if __name__ == "__main__":
    main()
