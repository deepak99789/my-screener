import streamlit as st
import yfinance as yf
import pandas as pd

# --- FIX: ROBUST DATA CLEANING ---
def clean_df(df):
    # Agar columns MultiIndex hain (yfinance ka naya format), toh unhe flatten karein
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    # Ensure column names match what we expect
    df.columns = [c.capitalize() for c in df.columns]
    # Agar 'Date' naam ka column nahi hai, toh pehle column ko Date banao
    if 'Date' not in df.columns:
        df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
    return df

def calculate_zones(df, base_list, legout_list):
    df = clean_df(df)
    zones = []
    target_b, target_l = max(base_list), max(legout_list)
    
    # Simple loop bina strict validation ke
    for i in range(target_b, len(df) - target_l):
        legin = df.iloc[i - target_b]
        bases = df.iloc[i - target_b + 1 : i]
        legouts = df.iloc[i : i + target_l]
        
        # Candle Strength: sirf 0.4 (40%) check kar rahe hain taaki zyaada zones milein
        high, low = float(legin['High']), float(legin['Low'])
        close, open_p = float(legin['Close']), float(legin['Open'])
        
        lr = high - low
        lb = abs(close - open_p)
        
        if lr > 0 and (lb / lr >= 0.4):
            pattern_dir = 'R' if close > open_p else 'D'
            zone_type = "Supply" if pattern_dir == 'R' else "Demand"
            
            # Simple Proximal/Distal
            prox = close if zone_type == "Demand" else open_p
            dist = low if zone_type == "Demand" else high
            
            zones.append({
                "Date": legin['Date'],
                "Pattern": pattern_dir,
                "Type": zone_type,
                "Proximal": round(prox, 2),
                "Distal": round(dist, 2),
                "Price": close
            })
    return pd.DataFrame(zones)

# --- EXECUTION ---
symbol = st.text_input("Enter Ticker (e.g., RELIANCE.NS)", "RELIANCE.NS")
if st.button("Run Scan"):
    df = yf.download(symbol, period="60d", interval="15m", progress=False)
    if not df.empty:
        res = calculate_zones(df, [1], [1])
        if not res.empty:
            st.success(f"Found {len(res)} zones!")
            st.dataframe(res)
        else:
            st.warning("Data mil gaya, lekin koi zone nahi mila. Pattern check karein.")
    else:
        st.error("Data download fail ho gaya.")
