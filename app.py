import streamlit as st
import yfinance as yf
import pandas as pd

# --- DATA CLEANER ---
def get_clean_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    df.columns = [c.capitalize() for c in df.columns]
    if 'Date' not in df.columns: df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
    return df

# --- PATTERN LOGIC ---
def scan_zones(df):
    zones = []
    # 3 candle pattern: Legin(i-2), Base(i-1), Legout(i)
    for i in range(2, len(df) - 1):
        legin = df.iloc[i-2]
        base = df.iloc[i-1]
        legout = df.iloc[i]
        
        # 1. Base ki Strength (Body small honi chahiye)
        base_body = abs(base['Close'] - base['Open'])
        base_range = base['High'] - base['Low']
        
        # 2. Legout ki Strength (Body badi honi chahiye)
        lo_body = abs(legout['Close'] - legout['Open'])
        lo_range = legout['High'] - legout['Low']
        
        # Pattern: RBR/DBD/RBD/DBR
        # Agar Base chota hai aur Legout bada hai, toh hi Zone hai
        if base_range > 0 and (base_body / base_range < 0.4) and (lo_body / lo_range > 0.6):
            
            zone_type = "Demand" if legout['Close'] > legout['Open'] else "Supply"
            prox = base['Close'] if zone_type == "Demand" else base['Open']
            dist = base['Low'] if zone_type == "Demand" else base['High']
            target = prox + (3*(prox-dist)) if zone_type == "Demand" else prox - (3*(dist-prox))
            
            zones.append({
                "Date": base['Date'],
                "Pattern": f"{'R' if legin['Close']>legin['Open'] else 'D'}B{'R' if legout['Close']>legout['Open'] else 'D'}",
                "Type": zone_type,
                "Proximal": round(prox, 2),
                "Distal": round(dist, 2),
                "Target": round(target, 2),
                "Status": "Fresh"
            })
    return pd.DataFrame(zones)

# --- APP UI ---
symbol = st.text_input("Stock Symbol", "RELIANCE.NS")
if st.button("Scan Patterns"):
    df = get_clean_data(symbol, "180d", "1h") # 1h timeframe is much more stable than 15m
    res = scan_zones(df)
    st.dataframe(res)
    st.download_button("Download", res.to_csv(index=False), "zones.csv")
