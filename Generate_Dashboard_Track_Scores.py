import pandas as pd
import os
import sys
import json

# CONFIGURATION
INPUT_CSV = "data.csv"
OUTPUT_HTML = "index.html"
HISTORY_FILE = "score_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_history(df, col_symbol, col_q, col_v, col_t):
    history = {}
    for _, row in df.iterrows():
        sym = str(row[col_symbol]).strip()
        history[sym] = {
            'q': float(row[col_q]) if col_q else 0,
            'v': float(row[col_v]) if col_v else 0,
            't': float(row[col_t]) if col_t else 0
        }
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def get_change_html(current_val, old_val):
    if old_val is None: return ""
    diff = current_val - old_val
    if diff > 0:
        return f'<span class="change-up">▲{int(diff)}</span>'
    elif diff < 0:
        return f'<span class="change-down">▼{int(abs(diff))}</span>'
    return ""

def main():
    print("--- TRACKING SCORE CHANGES FROM CSV ---")

    if not os.path.exists(INPUT_CSV):
        print(f"CRITICAL ERROR: {INPUT_CSV} not found.")
        sys.exit(1)

    # 1. READ DATA
    try:
        df = pd.read_csv(INPUT_CSV)
        df.columns = [c.strip().lower() for c in df.columns] # Standardize headers
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

    # 2. IDENTIFY COLUMNS (Auto-detect)
    col_symbol = next((c for c in df.columns if 'symbol' in c), None)
    col_name = next((c for c in df.columns if 'stock' in c and 'name' in c), None)
    # Flexible matching for score columns
    col_durability = next((c for c in df.columns if 'durability' in c), None)
    col_valuation = next((c for c in df.columns if 'valuation' in c), None)
    col_technicals = next((c for c in df.columns if 'momentum' in c), None)

    if not col_symbol:
        print("Error: CSV must have a 'Symbol' column.")
        sys.exit(1)

    # Clean data (ensure numbers)
    for col in [col_durability, col_valuation, col_technicals]:
        if col:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 3. COMPARE WITH HISTORY
    history = load_history()
    
    # 4. GENERATE HTML
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stock Score Tracker</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #eaedf2; padding: 20px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
            .card { background: white; border-radius: 12px; height: 450px; display: flex; flex-direction: column; overflow: hidden; }
            
            .card-header { 
                background: #f8f9fa; padding: 12px; border-bottom: 1px solid #eee; 
                display: flex; justify-content: space-between; align-items: center;
            }
            .symbol { font-weight: 800; color: #0056b3; font-size: 16px; }
            
            /* Score Board Styles */
            .score-row { 
                display: flex; justify-content: space-around; padding: 8px 0; background: #fff; border-bottom: 1px solid #f0f0f0; font-size: 13px;
            }
            .score-item { text-align: center; }
            .score-val { font-weight: bold; font-size: 14px; display: block; }
            .score-label { font-size: 11px; color: #666; text-transform: uppercase; }
            
            .change-up { color: #28a745; font-size: 11px; font-weight: bold; margin-left: 4px; }
            .change-down { color: #dc3545; font-size: 11px; font-weight: bold; margin-left: 4px; }

            .widget-box { flex-grow: 1; width: 100%; position: relative; }
        </style>
    </head>
    <body>
        <h2 style="text-align:center">Score Change Tracker</h2>
        <div class="grid">
    """

    for index, row in df.iterrows():
        sym = str(row[col_symbol]).strip()
        
        # Get Current Scores
        q_now = row[col_durability] if col_durability else 0
        v_now = row[col_valuation] if col_valuation else 0
        t_now = row[col_technicals] if col_technicals else 0
        
        # Get Past Scores
        past = history.get(sym, None)
        q_old = past['q'] if past else None
        v_old = past['v'] if past else None
        t_old = past['t'] if past else None

        # Build Change Indicators
        q_change = get_change_html(q_now, q_old)
        v_change = get_change_html(v_now, v_old)
        t_change = get_change_html(t_now, t_old)

        widget_code = f'<div class="trendlyne-widget" data-get-url="https://trendlyne.com/web-widget/checklist-widget/Poppins/{sym}/" data-theme="light"></div>'

        html += f"""
        <div class="card">
            <div class="card-header">
                <span class="symbol">{sym}</span>
            </div>
            
            <div class="score-row">
                <div class="score-item">
                    <span class="score-label">Quality</span>
                    <span class="score-val">{int(q_now)} {q_change}</span>
                </div>
                <div class="score-item">
                    <span class="score-label">Valuation</span>
                    <span class="score-val">{int(v_now)} {v_change}</span>
                </div>
                <div class="score-item">
                    <span class="score-label">Tech</span>
                    <span class="score-val">{int(t_now)} {t_change}</span>
                </div>
            </div>

            <div class="widget-box">
                {widget_code}
            </div>
        </div>
        """

    html += """
        </div>
        <script async src="https://cdn-static.trendlyne.com/static/js/webwidgets/tl-widgets.js" charset="utf-8"></script>
    </body>
    </html>
    """

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    
    # SAVE NEW HISTORY
    save_history(df, col_symbol, col_durability, col_valuation, col_technicals)
    print("SUCCESS: Dashboard updated with score changes.")

if __name__ == "__main__":
    main()
