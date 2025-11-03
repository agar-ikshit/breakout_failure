import streamlit as st
import pandas as pd
import time
from breakout.analyzer import analyze_vrz_vwap, plot_vrz_failures
from breakout.db import insert_failures
from breakout.settings import LOCAL_WINDOW, K_FACTOR, DEFAULT_INTERVAL, DEFAULT_PERIOD

# -------------------- Sample NIFTY 50 subset --------------------
NIFTY50_SAMPLE = {
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "Tata Consultancy Services",
    "HDFCBANK.NS": "HDFC Bank",
    "INFY.NS": "Infosys",
    "ICICIBANK.NS": "ICICI Bank"
}

# -------------------- Streamlit UI --------------------
st.set_page_config(page_title="Breakout Failures", layout="wide")
st.title("⚠️ Breakout Failures — Streamlit")

col1, col2 = st.columns([2, 1])

with col1:
    tickers_input = st.text_area("Tickers (comma separated)", value=",".join(NIFTY50_SAMPLE.keys()))
    interval = st.selectbox("Interval", options=["1m", "2m", "5m", "15m", "30m", "60m"], index=2)
    period = st.selectbox("Period", options=["1d", "5d", "7d", "1mo"], index=0)
    k = st.number_input("K factor (multiplier for ATR)", value=float(K_FACTOR))
    window = st.number_input("Local window (bars)", value=int(LOCAL_WINDOW), min_value=1, max_value=50)
    save_to_db = st.checkbox("Save results to Supabase", value=False)
    show_chart = st.checkbox("Show VRZ Charts", value=False)
    run_btn = st.button("Run analysis")

with col2:
    st.markdown("### Status")
    status = st.empty()
    spinner = st.empty()

# -------------------- Main Logic --------------------
if run_btn:
    tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]
    results = []
    status.text(f"Analyzing {len(tickers)} tickers...")
    prog = st.progress(0)

    for idx, t in enumerate(tickers, start=1):
        status.text(f"Analyzing {t} ({idx}/{len(tickers)})")
        spinner.info("Downloading and computing...")

        failures, df_price = analyze_vrz_vwap(
            t,
            NIFTY50_SAMPLE.get(t, t),
            k=k,
            window=window,
            interval=interval,
            period=period
        )

        if failures:
            results.extend(failures)

        prog.progress(idx / len(tickers))
        time.sleep(0.1)

    spinner.empty()
    status.empty()
    prog.empty()

    if not results:
        st.info("No breakout failures detected.")
    else:
        df = pd.DataFrame(results)
        df["failure_time"] = pd.to_datetime(df["failure_time"])
        df["Breakout Failure Time"] = df["failure_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df["Company Name"] = df["company"]
        df["Location"] = df["location"]

        # Add serial number
        df.insert(0, "S.No.", range(1, len(df) + 1))

        display_df = df[["S.No.", "Breakout Failure Time", "Company Name", "Location"]]
        st.dataframe(display_df, use_container_width=True)
        st.success(f"✅ Found {len(results)} breakout failures")

        # -------------------- Visualization Section --------------------
        if show_chart:
            st.markdown("### 📊 VRZ Breakout Failure Charts")
            for t in tickers:
                t_failures = [f for f in results if f["ticker"] == t]
                if not t_failures:
                    continue

                # Use the same df_price if cached, else re-run
                fig = plot_vrz_failures(df_price, t_failures, NIFTY50_SAMPLE.get(t, t), t)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

        # -------------------- Save to Supabase --------------------
        if save_to_db:
            st.info("Saving to Supabase...")
            payload = [
                {
                    "company": r["company"],
                    "ticker": r["ticker"],
                    "location": r["location"],
                    "failure_time": r["failure_time"].isoformat()
                    if hasattr(r["failure_time"], "isoformat")
                    else str(r["failure_time"]),
                }
                for r in results
            ]
            res = insert_failures(payload)
            if res.get("error"):
                st.error(f"Failed to save: {res['error']}")
            else:
                st.success("Saved results to Supabase ✅")
