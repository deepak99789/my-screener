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
with col5: scan_period = st.number_input("Scan Period (Days)", 1, 365, 30)

col6, col7, col8 = st.columns(3)
with col6: time_intervals = st.multiselect("Timeframe", ["5m", "15m", "1h", "4h", "1d"], default=["15m"])
with col7: zone_status = st.multiselect("Zone Status", ["Fresh", "Tested", "All"], default=["Fresh"])
with col8: zone_type = st.radio("Zone Type", ["Supply", "Demand", "All"], horizontal=True)

selected_symbols = st.multiselect("Select Symbols", TICKER_MAP[script_type], default=TICKER_MAP[script_type])
scan_button = st.button("🚀 RUN SCAN", use_container_width=True)

# --- STRATEGY ENGINE ---
def get_proximal_distal(base_candle, zone_type):
    is_green = base_candle['Close'] > base_candle['Open']
    if zone_type == "Demand":
        return (base_candle['Close'] if is_green else base_candle['Open']), base_candle['Low']
    else: # Supply
        return (base_candle['Open'] if is_green else base_candle['Close']), base_candle['High']

def calculate_zones(df, base_list, legout_list, validations):
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    if 'index' in df.columns: df.rename(columns={'index': 'Date'}, inplace=True)
    if 'Date' not in df.columns: df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
    
    def get_val(row, col):
        val = row[col]
        return float(val.iloc[0]) if isinstance(val, pd.Series) else float(val)

    zones = []
    target_b, target_l = max(base_list), max(legout_list)
    
    for i in range(target_b, len(df) - target_l - 1):
        legin = df.iloc[i - target_b]
        bases = df.iloc[i - target_b + 1 : i]
        legouts = df.iloc[i : i + target_l]
        
        # Validations
        if "Candle behind Legin" in validations:
            prev = df.iloc[i - target_b - 1]
            if get_val(legin, 'High') <= get_val(prev, 'High') and get_val(legin, 'Low') >= get_val(prev, 'Low'): continue
        if "White Area" in validations:
            f_l, l_b = legouts.iloc[0], bases.iloc[-1]
            if not (get_val(f_l, 'High') < get_val(l_b, 'Close') or get_val(f_l, 'Low') > get_val(l_b, 'Open')): continue
        
        high, low = get_val(legin, 'High'), get_val(legin, 'Low')
        close, open_p = get_val(legin, 'Close'), get_val(legin, 'Open')
        lr, lb = high - low, abs(close - open_p)
        
        if lr > 0 and (lb / lr >= 0.65):
            pattern_dir = 'R' if close > open_p else 'D'
            zone_type = "Supply" if pattern_dir == 'R' else "Demand"
            prox, dist = get_proximal_distal(bases.iloc[-1], zone_type)
            
            zone_price = get_val(legouts.iloc[0], 'Close')
            after_zone = df.iloc[i + target_l : ]
            is_tested = any((row['Low'] <= zone_price <= row['High']) for _, row in after_zone.iterrows())
            
            zones.append({
                "Date": legin['Date'],
                "Pattern": f"{pattern_dir}B{'R' if get_val(legouts.iloc[0], 'Close') > get_val(legouts.iloc[0], 'Open') else 'D'}",
                "Type": zone_type,
                "Proximal": round(float(prox), 2),
                "Distal": round(float(dist), 2),
                "Status": "Tested" if is_tested else "Fresh",
                "Price": zone_price
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
        st.download_button("📥 Download CSV", final_df.to_csv(index=False).encode('utf-8'), "scan_results.csv", "text/csv")
    else:
        st.warning("No zones found.")
