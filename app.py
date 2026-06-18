import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="Supply Demand Screener", layout="wide")

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
with col2: num_base = st.number_input("Base Candles", 1, 10, 2)
with col3: scan_period = st.number_input("Scan Period (Days)", 1, 365, 30)

selected_symbols = st.multiselect("Select Symbols", TICKER_MAP[script_type], default=TICKER_MAP[script_type])

col4, col5 = st.columns(2)
with col4: time_intervals = st.multiselect("Timeframes", ["5m", "15m", "1h", "4h", "1d"], default=["15m"])
with col5: zone_status = st.multiselect("Zone Status", ["Fresh", "Tested", "All"], default=["Fresh"])

col6, col7 = st.columns(2)
with col6: zone_type = st.radio("Zone Type", ["Supply", "Demand", "All"], horizontal=True)
with col7: dist_perc = st.slider("Distance to Entry (%)", 0.0, 10.0, 2.0, step=0.1)

scan_button = st.button("🚀 RUN SCAN", use_container_width=True)

# --- STRATEGY ENGINE ---
def calculate_zones(df, scan_period_days, base_limit):
    zones = []
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    if df.index.tz is not None: df.index = df.index.tz_localize(None)
    
    # Date Filtering
    cutoff_date = pd.to_datetime(datetime.now() - timedelta(days=scan_period_days))
    df = df[df.index >= cutoff_date].reset_index()
    # Ensure Date column name exists
    if 'Date' not in df.columns: df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
    
    for i in range(base_limit, len(df) - 1):
        legin = df.iloc[i - base_limit]
        legout = df.iloc[i + 1]
        
        lr, lb = float(legin['High'] - legin['Low']), float(abs(legin['Close'] - legin['Open']))
        
        if lr > 0 and (lb / lr >= 0.65):
            pattern = "Demand" if legin['Close'] < legin['Open'] else "Supply"
            zones.append({
                "Date of Zone Formed": legin['Date'],
                "Pattern": pattern,
                "Type": "Standard",
                "Status": "Fresh",
                "Base Count": base_limit,
                "Legout Count": 1,
                "Price": legout['Close']
            })
    return pd.DataFrame(zones)

# --- EXECUTION ---
if scan_button:
    results_list = []
    with st.spinner("Scanning markets..."):
        for symbol in selected_symbols:
            for tf in time_intervals:
                df = yf.download(symbol, period=f"{scan_period + 5}d", interval=tf, progress=False)
                if not df.empty:
                    res = calculate_zones(df, scan_period, num_base)
                    if not res.empty:
                        res['Symbol'] = symbol
                        res['Timeframe'] = tf
                        results_list.append(res)
    
    if results_list:
        final_df = pd.concat(results_list)
        if "All" not in zone_status: final_df = final_df[final_df['Status'].isin(zone_status)]
        if zone_type != "All": final_df = final_df[final_df['Pattern'] == zone_type]
        
        cols = ["Symbol", "Type", "Pattern", "Status", "Timeframe", "Base Count", "Legout Count", "Date of Zone Formed", "Price"]
        st.dataframe(final_df[cols], use_container_width=True)
        
        csv = final_df[cols].to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, "scan_results.csv", "text/csv")
    else:
        st.warning("No zones found. Try adjusting parameters.")
