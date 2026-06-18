import streamlit as st
import yfinance as yf
import pandas as pd

# --- CONFIGURATION ---
st.set_page_config(page_title="Pro Supply & Demand Screener", layout="wide")

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
with col2: scan_period = st.number_input("Scan Period (Days)", 1, 730, 180)
with col3: time_intervals = st.multiselect("Timeframe", ["15m", "1h", "4h", "1d"], default=["1h"])

# Filters
zone_type = st.radio("Zone Type", ["All", "Supply", "Demand"], horizontal=True)
zone_status_filter = st.multiselect("Filter Status", ["Fresh", "Tested", "Hit Target", "Hit SL"], default=["Fresh", "Tested"])
selected_symbols = st.multiselect("Select Symbols", TICKER_MAP[script_type], default=TICKER_MAP[script_type])

scan_button = st.button("🚀 RUN SCAN", use_container_width=True)

# --- CORE ENGINE ---
def get_clean_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    df.columns = [c.capitalize() for c in df.columns]
    if 'Date' not in df.columns: df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
    return df

def scan_zones(df):
    zones = []
    curr_price = float(df.iloc[-1]['Close'])
    for i in range(1, len(df)):
        base, legout = df.iloc[i-1], df.iloc[i]
        zt = "Demand" if legout['Close'] > legout['Open'] else "Supply"
        prox = base['Close']
        dist = base['Low'] if zt == "Demand" else base['High']
        risk = abs(prox - dist)
        if risk == 0: continue
        target = (prox + (3 * risk)) if zt == "Demand" else (prox - (3 * risk))
        
        status = "Hit Target" if (zt=="Demand" and curr_price>=target) or (zt=="Supply" and curr_price<=target) else \
                 "Hit SL" if (zt=="Demand" and curr_price<=dist) or (zt=="Supply" and curr_price>=dist) else "Fresh"
        
        zones.append({
            "Date": base['Date'], "Type": zt, "Proximal": round(prox, 2), 
            "Distal": round(dist, 2), "Target": round(target, 2), "Status": status,
            "Price": round(legout['Close'], 2)
        })
    return pd.DataFrame(zones)

# --- EXECUTION ---
if scan_button:
    results = []
    for sym in selected_symbols:
        for tf in time_intervals:
            df = get_clean_data(sym, f"{scan_period}d", tf)
            if not df.empty:
                res = scan_zones(df)
                res['Symbol'], res['Timeframe'] = sym, tf
                if zone_type != "All": res = res[res['Type'] == zone_type]
                if zone_status_filter: res = res[res['Status'].isin(zone_status_filter)]
                results.append(res)
    
    if results:
        final_df = pd.concat(results)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Zones", len(final_df))
        c2.metric("Target Hit", len(final_df[final_df['Status'] == 'Hit Target']))
        c3.metric("SL Hit", len(final_df[final_df['Status'] == 'Hit SL']))
        st.dataframe(final_df, use_container_width=True)
        st.download_button("📥 Download CSV", final_df.to_csv(index=False).encode('utf-8'), "scan_results.csv")
    else:
        st.warning("No zones found. Try relaxing filters.")
        
