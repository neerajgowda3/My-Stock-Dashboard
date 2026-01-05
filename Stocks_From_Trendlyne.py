import yfinance as yf
import re
import os
import urllib.parse
import time
from datetime import datetime
import pytz 

# --- CONFIGURATION ---
INPUT_FILE = "widgets.txt" 
OUTPUT_INDEX = "index.html"

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
    print("   CLOUD DASHBOARD (FINAL COSMETIC FIX)         ")
    print("------------------------------------------------")

    # 1. SETUP DATE STRINGS
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    date_filename = now.strftime("Dashboard_%d_%b.html")
    date_display = now.strftime("%d %b %Y")

    print(f"Report Date: {date_display}")

    # 2. READ FILE
    found_file = None
    for f in os.listdir('.'):
        if f.lower() == INPUT_FILE.lower():
            found_file = f
            break
    
    if not found_file:
        print(f"ERROR: Could not find '{INPUT_FILE}'.")
        return

    with open(found_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    stocks = []
    for line in lines:
        if "trendlyne-widgets" in line:
            sym = extract_symbol(line)
            if sym:
                stocks.append({'symbol': sym, 'code': line.strip(), 'mcap': 0.0})

    print(f">> Found {len(stocks)} stocks. Fetching data...")

    # 3. FETCH DATA
    for i, item in enumerate(stocks):
        if i % 10 == 0: print(f"Processing {i}/{len(stocks)}...", end='\r')
        item['mcap'] = get_market_cap(item['symbol'])
        time.sleep(0.05) 

    print("\n>> Sorting data...")
    stocks.sort(key=lambda x: (x['mcap'] or 0.0), reverse=True)

    # 4. GENERATE HTML (CSS UPDATED)
    html_start = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stock Dashboard</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #eaedf2; margin: 0; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 25px; color: #333; }}
            .sub-date {{ font-size: 14px; color: #666; margin-top: -15px; margin-bottom: 20px; display: block; }}
            
            .grid {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fill, minmax(23%, 1fr)); 
                gap: 20px; 
                width: 100%;
            }}
            
            .card {{ 
                background: white; 
                border-radius: 12px; 
                box-shadow: 0 4px 8px rgba(0,0,0,0.08); 
                display: flex; 
                flex-direction: column; 
                /* HEIGHT REDUCED FROM 450px to 400px TO REMOVE WHITE SPACE */
                height: 400px; 
                overflow: hidden; 
            }}
            
            .card-header {{ 
                background: #f8f9fa; 
                padding: 8px 15px; 
                border-bottom: 1px solid #eee; 
                font-size: 14px; 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                border-radius: 12px 12px 0 0;
            }}
            .symbol {{ font-weight: 800; color: #0056b3; font-size: 16px; }}
            .mcap {{ color: #666; font-size: 12px; }}
            .rank {{ background: #28a745; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
            
            /* Reduced padding to tighten layout */
            .widget-box {{ flex-grow: 1; position: relative; width: 100%; height: 100%; padding: 0px; }}
            
            @media (max-width: 768px) {{
                .grid {{ grid-template-columns: 1fr; }}
                .card {{ height: 450px; }} /* Keep taller on mobile just in case */
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Nifty 500 Dashboard (Ranked)</h2>
            <span class="sub-date">Date: {date_display}</span>
        </div>
        <div class="grid">
    """
    
    html_cards = ""
    for rank, item in enumerate(stocks, 1):
        mcap_display = f"₹{int(item['mcap']/10000000):,} Cr" if item['mcap'] > 0 else "N/A"
        
        html_cards += '<div class="card">'
        html_cards += f'<div class="card-header"><div><span class="symbol">{item["symbol"]}</span> <span class="mcap">({mcap_display})</span></div><span class="rank">#{rank}</span></div>'
        html_cards += f'<div class="widget-box">{item["code"]}</div>'
        html_cards += '</div>'

    html_end = """
        </div>
        <script async src="https://cdn-static.trendlyne.com/static/js/webwidgets/tl-widgets.js" charset="utf-8"></script>
    </body>
    </html>
    """
    
    full_html = html_start + html_cards + html_end

    with open(OUTPUT_INDEX, "w", encoding="utf-8") as f:
        f.write(full_html)
    
    with open(date_filename, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"\nSUCCESS! Generated with tight layout.")

if __name__ == "__main__":
    main()
