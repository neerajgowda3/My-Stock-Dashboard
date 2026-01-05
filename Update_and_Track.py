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
                data = json.load(f)
            # MIGRATION: Ensure all values are lists (for streak tracking)
            # If old format {'q': 50}, convert to {'q': [50]}
            for sym, scores in data.items():
                for key in ['q', 'v', 't']:
                    val = scores.get(key)
                    if isinstance(val, (int, float)):
                        scores[key] = [val]
            return data
        except:
            return {}
    return {}

def save_history(data):
    if len(data) > 0:
        with open(HISTORY_FILE, "w") as f:
            json.dump(data, f)

def get_score_color(score):
    if score >= 50: return "#009933" # Green
    elif score >= 30: return "#ff9900" # Orange
    else: return "#cc3300" # Red

def get_diff_html(current, history_list):
    if not history_list or not current: return ""
    prev = history_list[-1] # Last recorded score
    diff = current - prev
    
    if diff > 0:
        return f'<span style="color:#28a745; font-size:11px; font-weight:bold; margin-left:2px;">▲{int(diff)}</span>'
    elif diff < 0:
        return f'<span style="color:#dc3545; font-size:11px; font-weight:bold; margin-left:2px;">▼{int(abs(diff))}</span>'
    return ""

def get_streak_badge(history_list, current):
    # Check for 3-day rising streak
    # History has [Day-2, Day-1]. Current is Day-0.
    if len(history_list) >= 2:
        if current > history_list[-1] > history_list[-2]:
            return '<span style="background:#ffeeba; color:#856404; padding:1px 4px; border-radius:3px; font-size:10px; margin-left:5px;">🔥 Heat</span>'
    return ""

def main():
    print("--- STARTING: SCRAPE, TRACK, STREAK & ARCHIVE ---")
    
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
        print("Waiting for widgets...")
        try:
            WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.CLASS_NAME, "percent_number")))
            time.sleep(5) 
        except:
            print("Warning: Widgets slow.")

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

    # 4. PROCESS DATA
    print("Processing History & Identifying Movers...")
    history = load_history()
    
    # Structure for Top Movers Table
    top_movers = [] # List of tuples: (Symbol, Q_Change, T_Change)
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    
    grid = soup.find("div", class_="grid")
    if not grid: return

    raw_cards = grid.find_all("div", class_="card", recursive=False)
    cards_with_scores = []
    
    # Temporary storage for next history save
    new_history = {}

    for card in raw_cards:
        sym_tag = card.find("span", class_="symbol")
        if not sym_tag: continue
        sym = sym_tag.get_text().strip()
        
        curr = current_data.get(sym, {'q':0,'v':0,'t':0})
        hist = history.get(sym, {'q':[], 'v':[], 't':[]})
        
        # --- CALC METRICS ---
        q_badge = get_diff_html(curr['q'], hist['q'])
        v_badge = get_diff_html(curr['v'], hist['v'])
        t_badge = get_diff_html(curr['t'], hist['t'])
        
        q_streak = get_streak_badge(hist['q'], curr['q'])
        t_streak = get_streak_badge(hist['t'], curr['t'])
        
        # --- DETECT TOP MOVERS (Change >= 5) ---
        q_last = hist['q'][-1] if hist['q'] else curr['q']
        t_last = hist['t'][-1] if hist['t'] else curr['t']
        
        q_diff = curr['q'] - q_last
        t_diff = curr['t'] - t_last
        
        if abs(q_diff) >= 5 or abs(t_diff) >= 5:
            top_movers.append({
                'sym': sym,
                'q_diff': int(q_diff),
                't_diff': int(t_diff)
            })

        # --- UPDATE HISTORY (Keep last 3 days) ---
        new_history[sym] = {
            'q': (hist['q'] + [curr['q']])[-3:],
            'v': (hist['v'] + [curr['v']])[-3:],
            't': (hist['t'] + [curr['t']])[-3:]
        }
        
        # --- UPDATE HTML CARD ---
        score_row = card.find("div", class_="custom-score-row")
        if score_row: score_row.decompose()
            
        new_row = soup.new_tag("div", **{"class": "custom-score-row"})
        new_row['style'] = "display:flex; justify-content:space-around; background:#f9f9f9; padding:8px 5px; font-size:12px; border-bottom:1px solid #eee;"
        
        def create_col(label, val, badge, streak):
            color = get_score_color(val)
            div = soup.new_tag("div", style="text-align:center;")
            lbl = soup.new_tag("div", style="color:#666; font-size:10px; margin-bottom:2px;")
            lbl.string = label
            
            v_cont = soup.new_tag("div", style=f"font-weight:800; font-size:14px; color:{color};")
            v_cont.string = str(int(val))
            
            if badge: v_cont.append(BeautifulSoup(badge, "html.parser"))
            if streak: v_cont.append(BeautifulSoup(streak, "html.parser"))
                
            div.append(lbl)
            div.append(v_cont)
            return div

        new_row.append(create_col("Qual", curr['q'], q_badge, q_streak))
        new_row.append(create_col("Val", curr['v'], v_badge, ""))
        new_row.append(create_col("Tech", curr['t'], t_badge, t_streak))
        
        header = card.find("div", class_="card-header")
        if header: header.insert_after(new_row)
            
        cards_with_scores.append((curr['q'] + curr['t'], card))

    # 5. BUILD TOP MOVERS TABLE HTML
    if top_movers:
        # Sort by biggest change (absolute value)
        top_movers.sort(key=lambda x: max(abs(x['q_diff']), abs(x['t_diff'])), reverse=True)
        
        movers_html = """
        <div style="background:white; padding:15px; border-radius:10px; margin-bottom:20px; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
            <h3 style="margin-top:0; color:#333;">📊 Today's Top Movers</h3>
            <div style="overflow-x:auto;">
                <table style="width:100%; border-collapse:collapse; font-size:13px;">
                    <tr style="text-align:left; border-bottom:2px solid #eee;">
                        <th style="padding:8px;">Stock</th>
                        <th style="padding:8px;">Quality Change</th>
                        <th style="padding:8px;">Tech Change</th>
                    </tr>
        """
        for m in top_movers[:10]: # Show top 10 only
            q_style = "color:#28a745" if m['q_diff'] > 0 else "color:#dc3545" if m['q_diff'] < 0 else "color:#ccc"
            t_style = "color:#28a745" if m['t_diff'] > 0 else "color:#dc3545" if m['t_diff'] < 0 else "color:#ccc"
            
            q_arrow = f"▲{m['q_diff']}" if m['q_diff'] > 0 else f"▼{abs(m['q_diff'])}" if m['q_diff'] < 0 else "-"
            t_arrow = f"▲{m['t_diff']}" if m['t_diff'] > 0 else f"▼{abs(m['t_diff'])}" if m['t_diff'] < 0 else "-"

            movers_html += f"""
            <tr style="border-bottom:1px solid #f0f0f0;">
                <td style="padding:8px; font-weight:bold;">{m['sym']}</td>
                <td style="padding:8px; font-weight:bold; {q_style}">{q_arrow}</td>
                <td style="padding:8px; font-weight:bold; {t_style}">{t_arrow}</td>
            </tr>
            """
        movers_html += "</table></div></div>"
        
        # Insert Table before Grid
        movers_soup = BeautifulSoup(movers_html, "html.parser")
        grid.insert_before(movers_soup)

    # 6. SORT & SAVE
    cards_with_scores.sort(key=lambda x: x[0], reverse=True)
    grid.clear()
    for score, card in cards_with_scores:
        grid.append(card)
        
    final_html = str(soup)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_html)

    # 7. ARCHIVE (HTML + JSON)
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Save HTML Snapshot
    archive_html = os.path.join(ARCHIVE_DIR, f"dashboard_{today_str}.html")
    with open(archive_html, "w", encoding="utf-8") as f:
        f.write(final_html)
        
    # Save Data Snapshot (The Time Machine)
    archive_json = os.path.join(ARCHIVE_DIR, f"data_{today_str}.json")
    with open(archive_json, "w") as f:
        json.dump(current_data, f)
        
    print(f"SUCCESS: Archived HTML & JSON to {ARCHIVE_DIR}")

    # 8. SAVE UPDATED HISTORY
    save_history(new_history)

if __name__ == "__main__":
    main()
