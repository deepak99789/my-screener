import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Pro Supply Demand Screener", layout="wide")

TICKER_MAP = {
    "Nifty 50": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"],
    "US Stock 100": ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"],
    "Forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X"],
    "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD"]
}

# --- UI LAYER ---
st.title("🎯 Pro Supply & Demand Screener")

col1, col2, col3 = st.columns(3)
with col1: script_type = st.selectbox("Select Script Type", list(TICKER_MAP.keys()))
with col2: base_choice = st.multiselect("Base Candles", [1, 2, 3], default=[1])
with col3: legout_choice = st.multiselect("Legout Candles", [1, 2, 3], default=[1])

col4, col5 = st.columns(2)
with col4: validation_check = st.multiselect("Validation Filters", ["Candle behind Legin", "White Area"])
with col5: scan_period = st.number_input("Scan Period (Days)", 1, 365, 30)

col6, col7, col8 = st.columns(3)
with col6: time_intervals = st.multiselect("Timeframe", ["5m", "15m", "1h", "4h", "1d"], default=["15m"])
with col7: zone_status = st.multiselect("Zone Status", ["Fresh", "Tested", "All"], default=["Fresh"])
with col8: zone_type = st.radio("Zone Type", ["Supply", "Demand", "All"], horizontal=True)

selected_symbols = st.multiselect("Select Symbols", TICKER_MAP[script_type], default=TICKER_MAP[script_type])
scan_button = st.button("🚀 RUN SCAN", use_container_width=True)

# --- STRATEGY ENGINE ---
def calculate_zones(df, base_list, legout_list, validations):
    zones = []
    df = df.reset_index()
    if 'index' in df.columns: df.rename(columns={'index': 'Date'}, inplace=True)
    if 'Date' not in df.columns: df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
    
    max_b = max(base_list) if base_list else 1
    max_l = max(legout_list) if legout_list else 1
    
    for i in range(max_b, len(df) - max_l - 1):
        legin = df.iloc[i - max_b]
        bases = df.iloc[i - max_b + 1 : i]
        legouts = df.iloc[i : i + max_l]
        
        # Validation Logic
        if "Candle behind Legin" in validations:
            prev = df.iloc[i - max_b - 1]
            if float(legin['High']) <= float(prev['High']) and float(legin['Low']) >= float(prev['Low']): continue
        
        if "White Area" in validations:
            first_l = legouts.iloc[0]
            last_b = bases.iloc[-1]
            if not (float(first_l['High']) < float(last_b['Close']) or float(first_l['Low']) > float(last_b['Open'])): continue
        
        # Pattern Detection with Safe Float Conversion
        high = float(legin['High'])
        low = float(legin['Low'])
        close = float(legin['Close'])
        open_p = float(legin['Open'])
        
        lr = high - low
        lb = abs(close - open_p)
        
        if lr > 0 and (lb / lr >= 0.65):
            legout_first = legouts.iloc[0]
            pattern_dir = 'R' if close > open_p else 'D'
            legout_dir = 'R' if float(legout_first['Close']) > float(legout_first['Open']) else 'D'
            p_name = f"{pattern_dir}B{legout_dir}"
            
            zones.append({
                "Date": legin['Date'],
                "Pattern": p_name,
                "Type": "Supply" if pattern_dir == 'R' else "Demand",
                "Status": "Fresh",
                "Base Count": len(bases),
                "Legout Count": len(legouts),
                "Price": float(legout_first['Close'])
            })
    return pd.DataFrame(zones)

# --- EXECUTION ---
if scan_button:
    results_list = []
    with st.spinner("Scanning..."):
        for symbol in selected_symbols:
            for tf in time_intervals:
                df = yf.download(symbol, period=f"{scan_period + 5}d", interval=tf, progress=False)
                if not df.empty:
                    res = calculate_zones(df, base_choice, legout_choice, validation_check)
                    if not res.empty:
                        res['Symbol'] = symbol
                        res['Timeframe'] = tf
                        if "All" not in zone_status: res = res[res['Status'].isin(zone_status)]
                        if zone_type != "All": res = res[res['Type'] == zone_type]
                        results_list.append(res)
    
    if results_list:
        final_df = pd.concat(results_list)
        st.dataframe(final_df, use_container_width=True)
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, "scan_results.csv", "text/csv")
    else:
        st.warning("No zones found. Try adjusting parameters.")
