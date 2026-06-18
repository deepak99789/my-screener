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

col4, col5 = st.columns(2)
with col4: validation_check = st.multiselect("Validation Filters", ["Candle behind Legin", "White Area"])
with col5: scan_period = st.number_input("Scan Period (Days)", 1, 730, 360)

col6, col7, col8 = st.columns(3)
with col6: time_intervals = st.multiselect("Timeframe", ["15m", "1h", "4h", "1d"], default=["1h"])
with col7: zone_status = st.multiselect("Zone Status", ["Fresh", "Tested", "Hit Target", "Hit SL", "All"], default=["Fresh", "Tested"])
with col8: zone_type = st.radio("Zone Type", ["Supply", "Demand", "All"], horizontal=True)

selected_symbols = st.multiselect("Select Symbols", TICKER_MAP[script_type], default=TICKER_MAP[script_type])
scan_button = st.button("🚀 RUN SCAN", use_container_width=True)

# --- ENGINE ---
def get_clean_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    df.columns = [c.capitalize() for c in df.columns]
    if 'Date' not in df.columns: df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
    return df

def scan_zones(df, target_b, target_l):
    zones = []
    # Loop to capture pattern: Legin + Base + Legout
    for i in range(target_b + 1, len(df) - target_l):
        base = df.iloc[i-1]
        legout = df.iloc[i]
        
        base_body = abs(base['Close'] - base['Open'])
        base_range = base['High'] - base['Low']
        lo_body = abs(legout['Close'] - legout['Open'])
        lo_range = legout['High'] - legout['Low']
        
        # Valid Pattern Check (Base weak, Legout strong)
        if base_range > 0 and (base_body / base_range < 0.4) and (lo_body / lo_range > 0.6):
            zt = "Demand" if legout['Close'] > legout['Open'] else "Supply"
            prox = base['Close'] if zt == "Demand" else base['Open']
            dist = base['Low'] if zt == "Demand" else base['High']
            risk = abs(prox - dist)
            target = (prox + (3 * risk)) if zt == "Demand" else (prox - (3 * risk))
            
            zones.append({
                "Date": base['Date'],
                "Type": zt,
                "Proximal": round(prox, 2),
                "Distal": round(dist, 2),
                "Target": round(target, 2),
                "Status": "Fresh",
                "Base Count": target_b,
                "Legout Count": target_l,
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
                res = scan_zones(df, max(base_choice), max(legout_choice))
                if not res.empty:
                    res['Symbol'] = sym
                    res['Timeframe'] = tf
                    results.append(res)
    
    if results:
        final_df = pd.concat(results)
        st.dataframe(final_df, use_container_width=True)
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, "scan_results.csv", "text/csv")
    else:
        st.warning("No zones found with these settings.")
