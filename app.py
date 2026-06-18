import streamlit as st
import yfinance as yf
import pandas as pd

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

col4, col5, col6 = st.columns(3)
with col4: scan_period = st.number_input("Scan Period (Days)", 1, 730, 360)
with col5: time_intervals = st.multiselect("Timeframe", ["15m", "1h", "4h", "1d"], default=["1h"])
with col6: zone_type = st.radio("Zone Type", ["All", "Supply", "Demand"], horizontal=True)

# Status Filter wapis add kiya
zone_status_filter = st.multiselect("Filter by Zone Status", ["Fresh", "Tested", "Hit Target", "Hit SL"], default=["Fresh", "Tested"])

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

def scan_zones(df, target_b, target_l):
    zones = []
    for i in range(target_b + 1, len(df) - target_l):
        base = df.iloc[i-1]
        legout = df.iloc[i]
        
        base_body, base_range = abs(base['Close'] - base['Open']), (base['High'] - base['Low'])
        lo_body, lo_range = abs(legout['Close'] - legout['Open']), (legout['High'] - legout['Low'])
        
        if base_range > 0 and (base_body / base_range < 0.4) and (lo_body / lo_range > 0.6):
            zt = "Demand" if legout['Close'] > legout['Open'] else "Supply"
            prox, dist = (base['Close'] if zt == "Demand" else base['Open']), (base['Low'] if zt == "Demand" else base['High'])
            risk = abs(prox - dist)
            target = (prox + (3 * risk)) if zt == "Demand" else (prox - (3 * risk))
            
            curr_price = df.iloc[-1]['Close']
            status = "Hit Target" if (zt=="Demand" and curr_price>=target) or (zt=="Supply" and curr_price<=target) else \
                     "Hit SL" if (zt=="Demand" and curr_price<=dist) or (zt=="Supply" and curr_price>=dist) else "Fresh"
            
            zones.append({
                "Date": base['Date'], "Type": zt, "Proximal": round(prox, 2), "Distal": round(dist, 2),
                "Target": round(target, 2), "Status": status, "Base": target_b, "Legout": target_l, "Price": round(legout['Close'], 2)
            })
    return pd.DataFrame(zones)

# --- EXECUTION & SUMMARY ---
if scan_button:
    results = []
    for sym in selected_symbols:
        for tf in time_intervals:
            df = get_clean_data(sym, f"{scan_period}d", tf)
            if not df.empty:
                res = scan_zones(df, max(base_choice), max(legout_choice))
                if not res.empty:
                    res['Symbol'], res['Timeframe'] = sym, tf
                    # Apply Filters
                    if zone_type != "All": res = res[res['Type'] == zone_type]
                    if zone_status_filter: res = res[res['Status'].isin(zone_status_filter)]
                    results.append(res)
    
    if results:
        final_df = pd.concat(results)
        # Metrics update
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Zones", len(final_df))
        c2.metric("Target Hit", len(final_df[final_df['Status'] == 'Hit Target']))
        c3.metric("SL Hit", len(final_df[final_df['Status'] == 'Hit SL']))
        st.dataframe(final_df, use_container_width=True)
        st.download_button("📥 Download CSV", final_df.to_csv(index=False).encode('utf-8'), "scan_results.csv")
    else:
        st.warning("No zones found with these filters.")
