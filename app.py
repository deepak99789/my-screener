import streamlit as st
import yfinance as yf
import pandas as pd

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
with col5: val_type = st.multiselect("Validation Type", ["Candle behind Legin", "White Area"])

scan_button = st.button("🚀 RUN SCAN", use_container_width=True)

# --- STRATEGY ENGINE ---
def calculate_zones(df, legout_min_perc=70):
    zones = []
    # Data Cleaning: Multi-index issue fix
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Reset index to access by integer position
    df = df.reset_index(drop=True)
    
    for i in range(1, len(df) - 1):
        legin = df.iloc[i-1]
        base = df.iloc[i]
        legout = df.iloc[i+1]
        
        # Safe extraction
        try:
            lr, lb = float(legin['High'] - legin['Low']), float(abs(legin['Close'] - legin['Open']))
            br, bb = float(base['High'] - base['Low']), float(abs(base['Close'] - base['Open']))
            or_r, or_b = float(legout['High'] - legout['Low']), float(abs(legout['Close'] - legout['Open']))
            
            cond1 = (lb / lr) >= 0.65 if lr > 0 else False
            cond2 = (bb <= (lb / 2)) and (br <= (lr / 2))
            cond3 = (or_b / or_r >= (legout_min_perc/100)) if or_r > 0 else False

            if cond1 and cond2 and cond3:
                pattern = "Demand" if legin['Close'] < legin['Open'] else "Supply"
                zones.append({"Pattern": pattern, "Price": legout['Close']})
        except: continue
            
    return pd.DataFrame(zones)

# --- EXECUTION ---
if scan_button:
    results_list = []
    with st.spinner("Scanning..."):
        for symbol in selected_symbols:
            for tf in time_intervals:
                df = yf.download(symbol, period=f"{scan_period}d", interval=tf, progress=False)
                if not df.empty:
                    res = calculate_zones(df)
                    if not res.empty:
                        res['Symbol'] = symbol
                        res['TF'] = tf
                        results_list.append(res)
    
    if results_list:
        st.dataframe(pd.concat(results_list), use_container_width=True)
    else:
        st.warning("No zones found. Try changing parameters.")
