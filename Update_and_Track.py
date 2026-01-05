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
            # Ensure format is list for streak tracking
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
    prev = history_list[-1]
    diff = current - prev
    if diff > 0:
        return f'<span style="color:#28a745; font-size:11px; font-weight:bold; margin-left:2px;">▲{int(diff)}</span>'
    elif diff < 0:
        return f'<span style="color:#dc3545; font-size:11px; font-weight:bold; margin-left:2px;">▼{int(abs(diff))}</span>'
    return ""

def get_streak_badge(history_list, current):
    if len(history_list) >= 2:
        if current > history_list[-1] > history_list[-2]:
            return '<span style="background:#ffeeba; color:#856404; padding:1px 4px; border-radius:3px; font-size:10px; margin-left:5px;">🔥 Heat</span>'
    return ""

# --- NEW: CUSTOM RANKING LOGIC ---
def get_tier_rank(q, v, t):
    """
    Returns a Rank (1=Best, 5=Worst) based on user's specific rules.
    """
    # Definitions
    g_q = q >= 50
    g_v = v >= 50
    g_t = t >= 50
    
    # 1. All 3 are Green
    if g_q and g_v and g_t:
        return 1
        
    # 2. Quality AND Technicals are Green
    if g_q and g_t:
        return 2
        
    # 3. Value AND (Quality OR Technicals) are Green
    if g_v and (g_q or g_t):
        return 3
        
    # 4. "Yellows" (Average >= 30)
    avg = (q + v + t) / 3
    if avg >= 30:
        return 4
        
    # 5. "Reds" (Everything else)
    return 5

def main():
    print("--- STARTING: SCRAPE, TIER SORT, TRACK & ARCHIVE ---")
    
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
    history = load_history()
    top_movers = []
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    
    grid = soup.find("div", class_="grid")
    if not grid: return

    raw_cards = grid.find_all("div", class_="card", recursive=False)
    
    # Store tuples: (Tier, TotalScore, CardObject)
    cards_for_sorting = []
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
        
        # Movers Logic
        q_last = hist['q'][-1] if hist['q'] else curr['q']
        t_last = hist['t'][-1] if hist['t'] else curr['t']
        if abs(curr['q'] - q_last) >= 5 or abs(curr['t'] - t_last) >= 5:
            top_movers.append({'sym': sym, 'q_diff': int(curr['q'] - q_last), 't_diff': int(curr['t'] - t_last)})

        new_history[sym] = {
            'q': (hist['q'] + [curr['q']])[-3:],
            'v': (hist['v'] + [curr['v']])[-3:],
            't': (hist['t'] + [curr['t']])[-3:]
        }
        
        # --- UPDATE HTML ---
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
            
        # --- CALCULATE RANK ---
        tier = get_tier_rank(curr['q'], curr['v'], curr['t'])
        total_score = curr['q'] + curr['v'] + curr['t']
        
        cards_for_sorting.append((tier, total_score, card))

    # 5. SORTING LOGIC
    # Sort Key: (Tier [Ascending], Total Score [Descending])
    # Tier 1 is better than Tier 2. Score 300 is better than 200.
    cards_for_sorting.sort(key=lambda x: (x[0], -x[1]))
    
    grid.clear()
    
    # 6. OPTIONAL: Add Table if Movers exist
    if top_movers:
        top_movers.sort(key=lambda x: max(abs(x['q_diff']), abs(x['t_diff'])), reverse=True)
        movers_html = """<div style="background:white; padding:15px; border-radius:10px; margin-bottom:20px; box-shadow:0 2px 4px rgba(0,0,0,0.05);"><h3 style="margin-top:0; color:#333;">📊 Today's Top Movers</h3><div style="overflow-x:auto;"><table style="width:100%; border-collapse:collapse; font-size:13px;"><tr style="text-align:left; border-bottom:2px solid #eee;"><th style="padding:8px;">Stock</th><th style="padding:8px;">Quality Change</th><th style="padding:8px;">Tech Change</th></tr>"""
        for m in top_movers[:10]:
            q_style = "color:#28a745" if m['q_diff'] > 0 else "color:#dc3545" if m['q_diff'] < 0 else "color:#ccc"
            t_style = "color:#28a745" if m['t_diff'] > 0 else "color:#dc3545" if m['t_diff'] < 0 else "color:#ccc"
            movers_html += f"""<tr style="border-bottom:1px solid #f0f0f0;"><td style="padding:8px; font-weight:bold;">{m['sym']}</td><td style="padding:8px; font-weight:bold; {q_style}">{m['q_diff']}</td><td style="padding:8px; font-weight:bold; {t_style}">{m['t_diff']}</td></tr>"""
        movers_html += "</table></div></div>"
        grid.insert_before(BeautifulSoup(movers_html, "html.parser"))

    for _, _, card in cards_for_sorting:
        grid.append(card)
        
    final_html = str(soup)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(final_html)

    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
    today_str = datetime.now().strftime("%Y-%m-%d")
    with open(os.path.join(ARCHIVE_DIR, f"dashboard_{today_str}.html"), "w", encoding="utf-8") as f:
        f.write(final_html)
    with open(os.path.join(ARCHIVE_DIR, f"data_{today_str}.json"), "w", encoding="utf-8") as f:
        json.dump(current_data, f)

    save_history(new_history)
    print("SUCCESS: Tiered Sorting Applied.")

if __name__ == "__main__":
    main()
