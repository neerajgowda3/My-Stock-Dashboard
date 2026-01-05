import pandas as pd
import os
import sys

# --- CONFIGURATION ---
INPUT_FILE = "index.html" 
OUTPUT_FILE = "index.html" 

def categorize_stock(row):
    # Thresholds
    GOOD_SCORE = 50 
    
    # Safe Get: Returns 0 if column is missing
    durability = row.get('Durability Score', 0)
    momentum = row.get('Momentum Score', 0)
    valuation = row.get('Valuation Score', 0)

    # TIER 1: Quality + Technicals
    if durability > GOOD_SCORE and momentum > GOOD_SCORE:
        return 1
    # TIER 2: Value
    elif valuation > GOOD_SCORE:
        return 2
    # TIER 3: Rest
    else:
        return 3

def main():
    print(f"--- STARTING SORT PROCESS FOR {INPUT_FILE} ---")
    
    if not os.path.exists(INPUT_FILE):
        print(f"CRITICAL ERROR: {INPUT_FILE} does not exist.")
        sys.exit(1) # Fail the workflow

    # Read HTML tables
    try:
        # header=0 tells pandas the first row contains column names
        dfs = pd.read_html(INPUT_FILE, header=0) 
        if not dfs:
            print("CRITICAL ERROR: No tables found in index.html")
            sys.exit(1)
        df = dfs[0]
        print(f"Successfully loaded table with {len(df)} rows.")
        print(f"Columns found: {list(df.columns)}") # PRINT COLUMNS FOR DEBUGGING
    except Exception as e:
        print(f"CRITICAL ERROR reading HTML: {e}")
        sys.exit(1)

    # CHECK FOR CRITICAL COLUMNS
    required_cols = ['Durability Score', 'Valuation Score', 'Momentum Score']
    missing_cols = [c for c in required_cols if c not in df.columns]
    
    if missing_cols:
        print(f"WARNING: Missing columns {missing_cols}.")
        print("Sorting might be inaccurate, but proceeding with available data.")
    
    # 1. CLEANUP & PREPARE
    for col in required_cols:
        if col in df.columns:
            # Force numeric, turn errors (like 'N/A') into 0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 2. CALCULATE AVERAGE SCORE
    # We calculate average based on whatever columns we actually found
    available_score_cols = [c for c in required_cols if c in df.columns]
    if available_score_cols:
        df['Average Score'] = df[available_score_cols].mean(axis=1).round(2)
    else:
        df['Average Score'] = 0
        print("WARNING: No score columns found. 'Average Score' set to 0.")

    # 3. SEGREGATE
    df['Rank_Tier'] = df.apply(categorize_stock, axis=1)

    # 4. SORT
    # Sort by Tier (Ascending), then Score (Descending)
    df = df.sort_values(by=['Rank_Tier', 'Average Score'], ascending=[True, False])

    # 5. BEAUTIFY
    tier_map = {1: "🔥 Quality + Technicals", 2: "💰 High Value", 3: "⚠️ Neutral / Others"}
    df['Category'] = df['Rank_Tier'].map(tier_map)

    # Reorder columns
    cols = list(df.columns)
    if 'Category' in cols: cols.insert(0, cols.pop(cols.index('Category')))
    if 'Average Score' in cols: cols.insert(1, cols.pop(cols.index('Average Score')))
    
    # Drop helper column
    final_df = df[cols].drop(columns=['Rank_Tier'])

    # 6. SAVE
    print(f"Saving sorted data to {OUTPUT_FILE}...")
    final_df.to_html(OUTPUT_FILE, index=False, escape=False, border=1)
    print("--- SUCCESS: REPORT SORTED AND SAVED ---")

if __name__ == "__main__":
    main()
