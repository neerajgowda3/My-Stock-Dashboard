import yfinance as yf
import re
import os
import urllib.parse
import time

# --- CONFIGURATION ---
INPUT_FILE = "widgets.txt"
OUTPUT_HTML = "index.html"

def extract_symbol(html_line):
    """Extracts 'RELIANCE' from the Trendlyne link."""
    match = re.search(r'Poppins/([^/]+)/', html_line)
    if match:
        sym = urllib.parse.unquote(match.group(1))
        return sym
    return None

def get_market_cap(symbol):
    """Fetches live Market Cap from Yahoo Finance."""
    try:
        # FIX 1: Do not remove '&'. Pass symbol directly with .NS suffix
        # Example: "M&M" becomes "M&M.NS" (Correct for Yahoo)
        y_sym = f"{symbol}.NS"
        
        ticker = yf.Ticker(y_sym)
        
        # FIX 2: Explicitly check if data exists to prevent NoneType error
        cap = ticker.fast_info['market_cap']
        
        if cap is None:
            return 0.0
            
        return float(cap)
        
    except Exception as e:
        # If any network error occurs, return 0.0 safely
        return 0.0

def main():
    print("------------------------------------------------")
    print("   MARKET CAP SORTER v2 (Crash Proof)           ")
    print("------------------------------------------------")

    # 1. READ WIDGETS
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: '{INPUT_FILE}' not found.")
        input("Press Enter to exit..."); return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    stocks = []
    print("Reading widgets...")
    
    for line in lines:
        if "trendlyne-widgets" in line:
            sym = extract_symbol(line)
            if sym:
                stocks.append({'symbol': sym, 'code': line.strip(), 'mcap': 0.0})

    print(f">> Found {len(stocks)} stocks. Fetching Market Caps...")
    print("   (This safely takes 2-4 minutes to avoid blocks)")

    # 2. FETCH MARKET CAPS
    for i, item in enumerate(stocks):
        # Visual progress bar
        print(f"[{i+1}/{len(stocks)}] Fetching {item['symbol']}...", end='\r')
        
        item['mcap'] = get_market_cap(item['symbol'])
        
        # FIX 3: Sleep to prevent "Operation timed out" errors
        time.sleep(0.2) 

    print("\n>> Fetching Complete! Sorting data...")

    # 3. SORT (Highest Market Cap First)
    # The 'or 0.0' acts as a double safety net
    stocks.sort(key=lambda x: (x['mcap'] or 0.0), reverse=True)

    # 4. GENERATE HTML
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Market Cap Dashboard</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #eaedf2; padding: 20px; }
            .header { 
                background: linear-gradient(to right, #0052D4, #4364F7, #6FB1FC); 
                color: white; padding: 20px; text-align: center; border-radius: 8px; margin-bottom: 25px;
            }
            .grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); 
                gap: 20px; 
            }
            .card { 
                background: white; border-radius: 12px; overflow: hidden; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
                display: flex; flex-direction: column; min-height: 280px;
            }
            .card-header {
                background: #f8f9fa; padding: 10px 15px; border-bottom: 1px solid #eee;
                display: flex; justify-content: space-between; align-items: center;
            }
            .rank { 
                background: #333; color: white; padding: 4px 8px; 
                border-radius: 4px; font-size: 0.85em; font-weight: bold; 
            }
            .rank.top50 { background: #28a745; } 
            .symbol { font-weight: 800; color: #2c3e50; font-size: 1.1em; }
            .val { font-size: 0.8em; color: #666; }
            .widget-area { flex-grow: 1; padding: 10px; display:flex; justify-content:center; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Market Dashboard</h1>
            <p>Sorted by Real-Time Market Cap</p>
        </div>
        <div class="grid">
    """

    for rank, item in enumerate(stocks, 1):
        rank_class = "top50" if rank <= 50 else ""
        
        # Format Market Cap for display (Trillions/Billions)
        mcap_display = "Data N/A"
        if item['mcap'] > 0:
            val_cr = item['mcap'] / 10000000
            mcap_display = f"₹{int(val_cr):,} Cr"

        html += f'''
        <div class="card">
            <div class="card-header">
                <div>
                    <span class="symbol">{item['symbol']}</span>
                    <br><span class="val">{mcap_display}</span>
                </div>
                <span class="rank {rank_class}">#{rank}</span>
            </div>
            <div class="widget-area">
                {item['code']}
            </div>
        </div>
        '''

    html += """
        </div>
        <script async src="https://cdn-static.trendlyne.com/static/js/webwidgets/tl-widgets.js" charset="utf-8"></script>
    </body>
    </html>
    """

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print("\n------------------------------------------------")
    print("   SUCCESS! OPEN FILE BELOW:                    ")
    print(f"   {OUTPUT_HTML}")
    print("------------------------------------------------")
    
    input("Press Enter to exit...")

if __name__ == "__main__":

    main()
