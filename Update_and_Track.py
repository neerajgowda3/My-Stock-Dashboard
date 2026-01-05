import time
import os
import json
from datetime import datetime
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
ARCHIVE_DIR = "archive"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_history(data):
    if len(data) > 0:
        with open(HISTORY_FILE, "w") as f:
            json.dump(data, f)

def get_diff_html(current, previous):
    if previous is None: return ""
    diff = current - previous
    if diff == 0: return ""
    
    if diff > 0:
        return f'<span style="color:#28a745; font-size:11px; font-weight:bold; margin-left:2px;">▲{int(diff)}</span>'
    elif diff < 0:
        return f'<span style="color:#dc3545; font-size:11px; font-weight:bold; margin-left:2px;">▼{int(abs(diff))}</span>'
    return ""

def get_score_color(score):
    """Returns the color code based on Trendlyne-like thresholds."""
    if score >= 50:
        return "#009933" # Trendlyne Green
    elif score >= 30:
        return "#ff9900" # Trendlyne Orange
    else:
        return "#cc3300" # Trendlyne Red

def main():
    print("--- STARTING: SCRAPE, SORT, TRACK, ARCHIVE & COLOR ---")
    
    # 1. SETUP CHROME
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    file_path = "file://" + os.path.abspath(INPUT_FILE)
    driver = webdriver.Chrome(options=chrome_options)
    current_data = {} 

    try:
        print("Loading page...")
        driver.get(file_path)
        print("Waiting for scores...")
        try:
            WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.CLASS_NAME, "percent_number")))
            time.sleep(5) 
        except:
            print("Warning: Widgets slow. Proceeding...")

        cards = driver.find_elements(By.CSS_SELECTOR, ".card")
        print(f"Scraping {len(cards)} cards...")
        
        for card in cards:
            try:
                sym = card.find_element(By.CSS_SELECTOR, ".symbol").text.strip()
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

    except Exception as e:
        print(f"Browser Error: {e}")
    finally:
        driver.quit()

    # 4. PROCESS HTML
    print("Updating HTML with Colors...")
    history = load_history()
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    
    grid = soup.find("div", class_="grid")
    if not grid: return

    raw_cards = grid.find_all("div", class_="card", recursive=False)
    cards_with_scores = []

    for card in raw_cards:
        sym_tag = card.find("span", class_="symbol")
        if not sym_tag: continue
        sym = sym_tag.get_text().strip()
        
        curr = current_data.get(sym, {'q':0,'v':0,'t':0})
        hist = history.get(sym, {})
        
        # Build Score Row
        score_row = card.find("div", class_="custom-score-row")
        if score_row: score_row.decompose()
            
        new_row = soup.new_tag("div", **{"class": "custom-score-row"})
        new_row['style'] = "display:flex; justify-content:space-around; background:#f9f9f9; padding:8px 5px; font-size:12px; border-bottom:1px solid #eee;"
        
        def create_col(label, val, old_val):
            badge = get_diff_html(val, old_val)
            color = get_score_color(val) # Get color based on score
            
            div = soup.new_tag("div", style="text-align:center;")
            
            lbl = soup.new_tag("div", style="color:#666; font-size:10px; margin-bottom:2px;")
            lbl.string = label
            
            # Apply Color to the Score Value
            v_cont = soup.new_tag("div", style=f"font-weight:800; font-size:14px; color:{color};")
            v_cont.string = str(int(val))
            
            if badge:
                b_soup = BeautifulSoup(badge, "html.parser")
                v_cont.append(b_soup)
                
            div.append(lbl)
            div.append(v_cont)
            return div

        new_row.append(create_col("Qual", curr['q'], hist.get('q')))
        new_row.append(create_col("Val", curr['v'], hist.get('v')))
        new_row.append(create_col("Tech", curr['t'], hist.get('t')))
        
        header = card.find("div", class_="card-header")
        if header: header.insert_after(new_row)
            
        cards_with_scores.append((curr['q'] + curr['t'], card))

    # 5. SORT & SAVE
    cards_with_scores.sort(key=lambda x: x[0], reverse=True)
    grid.clear()
    for score, card in cards_with_scores:
        grid.append(card)
        
    final_html = str(soup)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    archive_filename = os.path.join(ARCHIVE_DIR, f"dashboard_{today_str}.html")
    with open(archive_filename, "w", encoding="utf-8") as f:
        f.write(final_html)

    save_history(current_data)
    print("SUCCESS: Colors applied, Sorted & Saved.")

if __name__ == "__main__":
    main()
