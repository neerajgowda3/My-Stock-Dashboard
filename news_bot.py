import yfinance as yf
import pandas as pd
import feedparser
import requests
import os
import urllib.parse

# --- CONFIGURATION ---
# These will come from GitHub Secrets (so you don't expose them)
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
CHAT_ID = os.environ.get("TG_CHAT_ID")
MIN_GAIN = 3.0  # Alert if stock is up > 3%

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def get_news(symbol):
    # Search specifically for the stock + 'stock news india'
    query = urllib.parse.quote(f"{symbol} stock news india")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(rss_url)
    
    # Return top headline if it was published recently (logic handled by Google RSS sort)
    if feed.entries:
        return feed.entries[0].title, feed.entries[0].link
    return None, None

def main():
    print("Starting News Scan...")
    
    # 1. Get Nifty 500 List (Auto-download to be safe)
    try:
        url = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
        # Backup URL
        bkp = "https://www1.nseindia.com/content/indices/ind_nifty500list.csv"
        
        try:
            df = pd.read_csv(url)
        except:
            df = pd.read_csv(bkp)
            
        symbols = [s + ".NS" for s in df['Symbol'].tolist()]
    except:
        print("Using fallback list.")
        symbols = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']

    # 2. Get Prices (Batch for speed)
    # We only fetch stocks up > 3% to save News API calls
    try:
        data = yf.download(symbols, period="1d", progress=False)['Close']
    except:
        return

    if len(data) == 0: return

    # Simple logic: Compare Last Price vs Open Price
    current = data.iloc[-1]
    opens = data.iloc[0]

    for sym in symbols:
        try:
            curr_p = current.get(sym)
            open_p = opens.get(sym)
            
            # Crash safety (Handle NaN or None)
            if pd.isna(curr_p) or pd.isna(open_p): continue
            
            pct_change = ((curr_p - open_p) / open_p) * 100
            
            if pct_change > MIN_GAIN:
                clean_sym = sym.replace('.NS', '')
                print(f"Checking {clean_sym} (+{pct_change:.1f}%)")
                
                title, link = get_news(clean_sym)
                
                if title:
                    # Construct Message
                    msg = (f"🚀 <b>{clean_sym}</b> is up <b>{pct_change:.1f}%</b>\n\n"
                           f"📰 <a href='{link}'>{title}</a>")
                    send_telegram(msg)
        except:
            continue

if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: Secrets not set.")
    else:
        main()
