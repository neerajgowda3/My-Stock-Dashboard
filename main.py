import yfinance as yf
import re
import os
import urllib.parse
import time

# --- CONFIGURATION ---
# Note: Ensure this matches your file name exactly (Case Sensitive on GitHub!)
INPUT_FILE = "widgets.txt" 
OUTPUT_HTML = "index.html"

def extract_symbol(html_line):
    match = re.search(r'Poppins/([^/]+)/', html_line)
    if match:
        return urllib.parse.unquote(match.group(1))
    return None

def get_market_cap(symbol):
    try:
        y_sym = f"{symbol}.NS"
        ticker = yf.Ticker(y_sym)
        cap = ticker.fast_info['market_cap']
        return float(cap) if cap is not None else 0.0
    except:
        return 0.0

def main():
    print("------------------------------------------------")
    print("   CLOUD DASHBOARD (FIXED STRING ERROR)         ")
    print("------------------------------------------------")

    # Case-insensitive check for filename
    found_file = None
    for f in os.listdir('.'):
        if f.lower() == INPUT_FILE.lower():
            found_file = f
            break
    
    if not found_file:
        print(f"ERROR: Could not find '{INPUT_FILE}' (or 'Widgets.txt').")
        return

    print(f"Reading {found_file}...")
    with open(found_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    stocks = []
    
    for line in lines:
        if "trendlyne-widgets" in line:
            sym = extract_symbol(line)
            if sym:
                stocks.append({'symbol': sym, 'code': line.strip(), 'mcap': 0.0})

    print(f">> Found {len(stocks)} stocks. Fetching data...")

    for i, item in enumerate(stocks):
        if i % 10 == 0: print(f"Processing {i}/{len(stocks)}...", end='\r')
        item['mcap'] = get_market_cap(item['symbol'])
        time.sleep(0.05) 

    print("\n>> Sorting data...")
    stocks.sort(key=lambda x: (x['mcap'] or 0.0), reverse=True)

    # --- HTML GENERATION ---
    html_start = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stock Dashboard</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; padding: 10px; }
            .header { text-align: center; margin-bottom: 20px; color: #333; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; width: 100%; }
            .card { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; display: flex; flex-direction: column; height: 320px; }
            .card-header { background: #f8f9fa; padding: 8px 12px; border-bottom: 1px solid #eee; font-size: 14px; display: flex; justify-content: space-between; align-items: center; }
            .symbol { font-weight: bold; color: #0056b3; font-size: 16px; }
            .mcap { color: #666; font-size: 12px; }
            .rank { background: #28a745; color: white; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
            .widget-box { flex-grow: 1; position: relative; }
            iframe { width: 100% !important; height: 100% !important; border: none; }
        </style>
    </head>
    <body>
        <div class="header"><h3>Nifty 500 Dashboard (Ranked)</h3></div>
        <div class="grid">
    """
    
    html_cards = ""
    for rank, item in enumerate(stocks, 1):
        mcap_display = f"₹{int(item['mcap']/10000000):,} Cr" if item['mcap'] > 0 else "N/A"
        
        # Using simple f-string concatenation to avoid triple-quote errors
        html_cards += f'<div class="card">'
        html_cards += f'<div class="card-header"><div><span class="symbol">{item["symbol"]}</span> <span class="mcap">({mcap_display})</span></div><span class="rank">#{rank}</span></div>'
        html_cards += f'<div class="widget-box">{item["code"]}</div>'
        html_cards += f'</div>'

    html_end = """
        </div>
        <script async src="https://cdn-static.trendlyne.com/static/js/webwidgets/tl-widgets.js" charset="utf-8"></script>
    </body>
    </html>
    """

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_start + html_cards + html_end)

    print("\nSUCCESS! index.html generated.")

if __name__ == "__main__":
    main()
