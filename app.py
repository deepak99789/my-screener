import streamlit as st
import yfinance as yf
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Supply Demand Screener", layout="wide")

# Ticker Groups (Add more symbols here)
TICKER_MAP = {
    "Nifty 50": ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"],
    "US Stock 100": ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"],
    "Forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X"],
    "Crypto": ["BTC-USD", "ETH-USD", "SOL-USD"]
}

# --- UI LAYER ---
st.title("🎯 Pro Supply & Demand Screener")
st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    script_type = st.selectbox("Select Script Type", list(TICKER_MAP.keys()))
with col2:
    num_base = st.number_input("Base Candles", 1, 10, 2)
with col3:
    scan_period = st.number_input("Scan Period (Days)", 1, 365, 30)

selected_symbols = st.multiselect("Select Symbols", TICKER_MAP[script_type], default=TICKER_MAP[script_type])

col4, col5 = st.columns(2)
with col4:
    time_intervals = st.multiselect("Timeframes", ["5m", "15m", "1h", "4h", "1d"], default=["15m"])
with col5:
    val_type = st.multiselect("Validation Type", ["Candle behind Legin", "White Area"])

col6, col7, col8 = st.columns(3)
with col6:
    zone_status = st.multiselect("Zone Status", ["Fresh", "Target", "SL", "All"], default=["Fresh"])
with col7:
    zone_type = st.radio("Zone Type", ["Supply", "Demand", "All"], horizontal=True)
with col8:
    dist_perc = st.slider("Distance to Entry (%)", 0.0, 10.0, 2.0, step=0.1)

scan_button = st.button("🚀 RUN SCAN", use_container_width=True)

# --- STRATEGY ENGINE ---
def calculate_zones(df, base_candles, legout_min_perc=70):
    zones = []
    for i in range(1, len(df) - 1):
        legin, base, legout = df.iloc[i-1], df.iloc[i], df.iloc[i+1]
        
        # Metrics
        lr, lb = (legin['High'] - legin['Low']), abs(legin['Close'] - legin['Open'])
        br, bb = (base['High'] - base['Low']), abs(base['Close'] - base['Open'])
        or_r, or_b = (legout['High'] - legout['Low']), abs(legout['Close'] - legout['Open'])

        # Strategy Logic
        cond1 = (lb / lr) >= 0.65 if lr > 0 else False
        cond2 = (bb <= (lb / 2)) and (br <= (lr / 2))
        cond3 = (or_b / or_r >= (legout_min_perc/100)) if or_r > 0 else False

        if cond1 and cond2 and cond3:
            pattern = "Demand" if legin['Close'] > legin['Open'] else "Supply"
            zones.append({"Time": legin.name, "Pattern": pattern, "Price": legout['Close']})
    return pd.DataFrame(zones)

# --- EXECUTION ---
if scan_button:
    results_list = []
    with st.spinner("Scanning markets..."):
        for symbol in selected_symbols:
            for tf in time_intervals:
                df = yf.download(symbol, period=f"{scan_period}d", interval=tf, progress=False)
                if not df.empty:
                    res = calculate_zones(df, num_base)
                    if not res.empty:
                        res['Symbol'] = symbol
                        results_list.append(res)
    
    if results_list:
        final_df = pd.concat(results_list)
        st.success(f"Scan Finished! Found {len(final_df)} zones.")
        st.dataframe(final_df, use_container_width=True)
    else:
        st.warning("No zones found.")
