import streamlit as st
import yfinance as yf
import pandas as pd

# UI Config
st.set_page_config(page_title="Supply Demand Screener", layout="wide")
st.title("📊 Supply & Demand Strategy Screener")

# Sidebar - User Inputs
with st.sidebar:
    st.header("⚙️ Configuration")
    symbol = st.text_input("Enter Symbol (e.g. RELIANCE.NS, BTC-USD)", "RELIANCE.NS")
    timeframe = st.selectbox("Timeframe", ["5m", "15m", "30m", "45m", "1h", "2h", "4h", "1d", "1wk"])
    
    st.divider()
    st.subheader("Strategy Settings")
    base_candles = st.number_input("Base Candles (Count)", 1, 5, 2)
    legout_min_perc = st.slider("Legout Body Requirement (%)", 50, 100, 70)
    
    run_btn = st.button("🚀 Run Analysis")

# Strategy Logic
def calculate_zones(df, legout_min_perc):
    zones = []
    # Loop through candles to find 3-candle patterns
    for i in range(1, len(df) - 1):
        legin, base, legout = df.iloc[i-1], df.iloc[i], df.iloc[i+1]
        
        # Calculate Range and Body
        def get_metrics(candle):
            r = candle['High'] - candle['Low']
            b = abs(candle['Close'] - candle['Open'])
            return r, b

        lr, lb = get_metrics(legin)
        br, bb = get_metrics(base)
        or_r, or_b = get_metrics(legout)

        # Conditions
        cond1 = (lb / lr) >= 0.65 if lr > 0 else False
        cond2 = (bb <= (lb / 2)) and (br <= (lr / 2))
        cond3 = (or_b / or_r >= (legout_min_perc/100)) and (or_b > lb)

        if cond1 and cond2 and cond3:
            # Pattern classification
            if legin['Close'] > legin['Open'] and legout['Close'] > legout['Open']: pattern = "RBR (Demand)"
            elif legin['Close'] > legin['Open'] and legout['Close'] < legout['Open']: pattern = "RBD (Supply)"
            elif legin['Close'] < legin['Open'] and legout['Close'] < legout['Open']: pattern = "DBD (Supply)"
            else: pattern = "DBR (Demand)"
            
            zones.append({"Time": legin.name, "Pattern": pattern, "Price": legout['Close']})
    return pd.DataFrame(zones)

# Execution
if run_btn:
    with st.spinner("Analyzing data..."):
        data = yf.download(symbol, period="1mo", interval=timeframe)
        if not data.empty:
            results = calculate_zones(data, legout_min_perc)
            if not results.empty:
                st.success(f"Zones Found: {len(results)}")
                st.table(results)
            else:
                st.warning("No zones found matching your criteria.")
        else:
            st.error("Invalid symbol or no data available.")
