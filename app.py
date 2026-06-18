import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# --- STRATEGY ENGINE (UPDATED) ---
def calculate_zones(df, scan_period_days, base_candles_limit):
    zones = []
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    if df.index.tz is not None: df.index = df.index.tz_localize(None)
    
    cutoff_date = pd.to_datetime(datetime.now() - timedelta(days=scan_period_days))
    df = df[df.index >= cutoff_date]
    df = df.reset_index() # Date ko column banane ke liye
    
    # Loop range: base_candles ko track karne ke liye
    for i in range(base_candles_limit, len(df) - 1):
        legin = df.iloc[i - base_candles_limit - 1]
        legout = df.iloc[i + 1]
        
        # Simple Logic for Pattern Identification
        lr = float(legin['High'] - legin['Low'])
        lb = float(abs(legin['Close'] - legin['Open']))
        
        if lr > 0 and (lb / lr >= 0.65):
            pattern = "Demand" if legin['Close'] < legin['Open'] else "Supply"
            
            zones.append({
                "Date of Zone Formed": legin['Date'],
                "Pattern": pattern,
                "Type": "Standard", # Aap ise logic se badal sakte hain
                "Status": "Fresh",
                "Base Count": base_candles_limit,
                "Legout Count": 1,
                "Price": legout['Close']
            })
    return pd.DataFrame(zones)

# --- EXECUTION (INTEGRATED) ---
if scan_button:
    results_list = []
    with st.spinner("Scanning..."):
        for symbol in selected_symbols:
            for tf in time_intervals:
                df = yf.download(symbol, period=f"{scan_period + 5}d", interval=tf, progress=False)
                if not df.empty:
                    res = calculate_zones(df, scan_period, num_base)
                    if not res.empty:
                        # Adding requested columns
                        res['Symbol'] = symbol
                        res['Timeframe'] = tf
                        
                        # Reordering columns for the final table
                        cols = ["Symbol", "Type", "Pattern", "Status", "Timeframe", 
                                "Base Count", "Legout Count", "Date of Zone Formed", "Price"]
                        results_list.append(res[cols])
    
    if results_list:
        final_df = pd.concat(results_list)
        st.dataframe(final_df, use_container_width=True)
        
        # CSV Download Button
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, "results.csv", "text/csv")
