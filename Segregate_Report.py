import pandas as pd
import os
import sys

INPUT_FILE = "index.html" 
OUTPUT_FILE = "index.html" 

def main():
    print(f"--- DEBUGGING {INPUT_FILE} ---")
    
    # Check if file exists
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: {INPUT_FILE} does not exist.")
        sys.exit(1)
        
    # READ AND PRINT THE FILE CONTENT
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        
    print(f"File Size: {len(content)} bytes")
    print("--- START OF FILE CONTENT ---")
    print(content[:1000]) # Print first 1000 characters
    print("--- END OF FILE CONTENT ---")

    if len(content) < 50:
        print("CRITICAL: File is too small/empty. Stocks_From_Trendlyne.py failed to write data.")
        sys.exit(1)

    # ... The rest of the sorting logic would go here ...
    # But for now, we just want to see why it is empty.

if __name__ == "__main__":
    main()
