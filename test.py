import yfinance as yf
import pandas as pd

def test_yfinance_data(symbol="RELIANCE.NS", period="5d", interval="15m"):
    print(f"Fetching {symbol} data from Yahoo Finance...")

    try:
        # Fetch recent data
        df = yf.download(symbol, period=period, interval=interval, progress=False)

        if df.empty:
            print("❌ No data returned! Check the symbol or network.")
            return

        # Display basic info
        print("\n✅ Data fetched successfully!\n")
        print(df.head(10))

        # Show column names and types
        print("\n📊 Columns and types:")
        print(df.dtypes)

        # Check if required columns exist
        required_cols = {"Open", "High", "Low", "Close", "Volume"}
        if required_cols.issubset(df.columns):
            print("\n✅ All OHLCV columns are present.")
        else:
            print("\n⚠️ Missing columns:", required_cols - set(df.columns))

        # Show date range and frequency
        print(f"\n📅 Date Range: {df.index.min()} → {df.index.max()}")
        print(f"🕒 Total records: {len(df)}")

    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")

if __name__ == "__main__":
    test_yfinance_data()
