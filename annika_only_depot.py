import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import pytz
import os
import json

# ------------------
# Global Configurations
# ------------------
LOCAL_TZ = pytz.timezone("Europe/Berlin")
DATA_FILE_PATH = "parents_data.json"
INITIAL_CASH = 17000

# Define your portfolio assets. Note: using lowercase keys for consistency.
PORTFOLIO_ASSETS = [
    {"ticker": "URTH", "quantity": 480, "name": "Welt Index"},
    {"ticker": "WFC", "quantity": 400, "name": "Wells Fargo (Bank)"},
    {"ticker": "HLBZF", "quantity": 185, "name": "Heidelberg Materials"},
    {"ticker": "C", "quantity": 340, "name": "Citigroup (Bank)"},
    {"ticker": "BPAQF", "quantity": 2000, "name": "British Petroleum (Öl/Gas)"},
    {"ticker": "POAHF", "quantity": 150, "name": "Porsche (Auto)"},
    {"ticker": "EXV1.DE", "quantity": 284, "name": "Bank Index"},
    {"ticker": "1COV.DE", "quantity": 100, "name": "Covestro (Chemie)"},
    {"ticker": "SPY", "quantity": 10, "name": "USA Index"},
    {"ticker": "HYMTF", "quantity": 100, "name": "Hyundai (Auto)"},
    {"ticker": "SHEL", "quantity": 75, "name": "Shell (Öl/Gas)"},
    {"ticker": "DAX", "quantity": 6, "name": "Deutschland Index"},
    {"ticker": "PLTR", "quantity": 100, "name": "Palantir (Rüstung Software)"},
    {"ticker": "UQ2B.DU", "quantity": 5, "name": "Europa Index"},
    {"ticker": "DB", "quantity": 1, "name": "Deutsche Bank"},
    {"ticker": "GS", "quantity": 9, "name": "Goldman Sachs (Bank)"},
    {"ticker": "MBG.DE", "quantity": 50, "name": "Mercedes (Auto)"},
]

# ------------------
# Data Loading and Fetching Functions
# ------------------
def load_ownership_data():
    """
    Load ownership data from a JSON file. The value is expected either as a fraction (e.g. 0.29 for 29%)
    or as a percentage (e.g. 29 for 29%).
    """
    default_ownership = 0.294365599  # 29.44% as fraction
    if os.path.exists(DATA_FILE_PATH):
        try:
            with open(DATA_FILE_PATH, "r") as file:
                data = json.load(file)
                percentage = data.get("ownership", default_ownership)
                # if percentage > 1, assume it's provided as a percentage
                return percentage / 100.0 if percentage > 1 else percentage
        except json.JSONDecodeError:
            st.warning("Data file is corrupt. Using default ownership value.")
    return default_ownership

def fetch_daily_data(ticker, period="7d", interval="1d"):
    """Fetch recent daily data for a given ticker."""
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if not df.empty:
            # First localize to UTC then convert to the local timezone.
            df.index = df.index.tz_localize('UTC').tz_convert(LOCAL_TZ)
            return df
    except Exception as e:
        st.error(f"Error fetching daily data for {ticker}: {e}")
    return pd.DataFrame()

def fetch_all_daily_data(tickers, period="7d", interval="1d"):
    """Fetch daily data for all tickers."""
    data = {}
    for ticker in tickers:
        data[ticker] = fetch_daily_data(ticker, period, interval)
    return data

def fetch_historical_data(ticker, period="1y", interval="1d"):
    """Fetch historical daily data for a given ticker over 1 year."""
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if not df.empty:
            df.index = df.index.tz_localize('UTC').tz_convert(LOCAL_TZ)
            return df
    except Exception as e:
        st.error(f"Error fetching historical data for {ticker}: {e}")
    return pd.DataFrame()

def fetch_all_historical_data(tickers, period="1y", interval="1d"):
    """Fetch historical data for all tickers."""
    data = {}
    for ticker in tickers:
        data[ticker] = fetch_historical_data(ticker, period, interval)
    return data

# ------------------
# Calculation Functions
# ------------------
def calculate_portfolio_value(target_date, price_data, portfolio=PORTFOLIO_ASSETS, initial_cash=INITIAL_CASH):
    """
    Calculate the portfolio value on a given date.
    price_data should be a dict mapping tickers to their DataFrame of daily data.
    """
    total = initial_cash
    for asset in portfolio:
        ticker = asset["ticker"]
        quantity = asset["quantity"]
        df = price_data.get(ticker)
        if df is not None and not df.empty:
            # Get the last available close on or before the target date
            df_on_date = df[df.index.date <= target_date]
            if not df_on_date.empty:
                price = df_on_date.iloc[-1]["Close"]
                total += price * quantity
    return total

def create_chart_dataframe(historical_data, portfolio=PORTFOLIO_ASSETS, initial_cash=INITIAL_CASH):
    """
    Build a DataFrame containing dates and portfolio values computed from historical data.
    """
    # Get the union of dates from all tickers
    dates = set()
    for df in historical_data.values():
        if not df.empty:
            dates.update(df.index.date)
    sorted_dates = sorted(dates)
    
    chart_rows = []
    for d in sorted_dates:
        value = calculate_portfolio_value(d, historical_data, portfolio, initial_cash)
        chart_rows.append({"Date": pd.Timestamp(d), "Portfolio Value": value})
    df_chart = pd.DataFrame(chart_rows)
    df_chart.sort_values("Date", inplace=True)
    return df_chart

# ------------------
# Main App Function
# ------------------
def main():
    st.title("Anni's Aktien – Robust Version")
    ownership_fraction = load_ownership_data()

    tickers = [asset["ticker"] for asset in PORTFOLIO_ASSETS]
    
    # Fetch data
    daily_data = fetch_all_daily_data(tickers, period="7d", interval="1d")
    historical_data = fetch_all_historical_data(tickers, period="1y", interval="1d")
    
    today = datetime.now(LOCAL_TZ).date()
    current_value = calculate_portfolio_value(today, daily_data, PORTFOLIO_ASSETS, INITIAL_CASH)
    current_share_value = current_value * ownership_fraction

    # For the "since yesterday" metric, use the last two available trading days
    yesterday_value = None
    for ticker, df in daily_data.items():
        if df is not None and len(df) >= 2:
            # Assuming the DataFrame is sorted by date, get the second-to-last closing price
            pass  # We will compute on an aggregated level
    # Instead, compute the portfolio value as of the most recent day before today.
    previous_dates = []
    for df in daily_data.values():
        if df is not None and not df.empty:
            last_date = df.index.date[-1]
            if last_date < today:
                previous_dates.append(last_date)
    if previous_dates:
        last_trading_day = max(previous_dates)
        yesterday_value = calculate_portfolio_value(last_trading_day, daily_data, PORTFOLIO_ASSETS, INITIAL_CASH)
        yesterday_share_value = yesterday_value * ownership_fraction
        delta_value = current_share_value - yesterday_share_value
        delta_percent = (delta_value / yesterday_share_value * 100) if yesterday_share_value else 0
    else:
        yesterday_share_value = None
        delta_value = None
        delta_percent = None

    # Display metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Aktueller Wert",
            value=f"€{current_share_value:,.2f}",
            # Here the delta compared to an arbitrary baseline is shown (you might adjust as needed)
            delta=f"{((current_share_value - 650) / 650) * 100:.2f}%",
            delta_color="normal"
        )
    with col2:
        if yesterday_share_value is not None:
            st.metric(
                label="Seit gestern",
                value=f"€{delta_value:+,.2f}",
                delta=f"{delta_percent:+.2f}%",
                delta_color="normal"
            )
        else:
            st.metric("Seit gestern", "N/A")

    # Chart: Portfolio value evolution over the last 12 months
    st.subheader("Wertentwicklung des Depots über 12 Monate")
    chart_df = create_chart_dataframe(historical_data, PORTFOLIO_ASSETS, INITIAL_CASH)
    if not chart_df.empty:
        # Ensure Date is localized
        chart_df["Date"] = pd.to_datetime(chart_df["Date"]).dt.tz_localize(LOCAL_TZ)
        st.line_chart(chart_df.set_index("Date")["Portfolio Value"])
    else:
        st.write("Keine historischen Daten verfügbar.")

    # Calculate performance per asset for the latest day change using daily_data.
    performance_data = []
    best_pct = {"name": None, "value": -float('inf')}
    best_gain = {"name": None, "value": -float('inf')}
    
    for asset in PORTFOLIO_ASSETS:
        ticker = asset["ticker"]
        df = daily_data.get(ticker)
        if df is not None and len(df) >= 2:
            df_sorted = df.sort_index()
            latest_close = df_sorted.iloc[-1]["Close"]
            previous_close = df_sorted.iloc[-2]["Close"]
            delta_price = latest_close - previous_close
            delta_pct = (delta_price / previous_close * 100) if previous_close else 0
            total_gain = delta_price * asset["quantity"] * ownership_fraction
            if delta_pct > best_pct["value"]:
                best_pct = {"name": asset["name"], "value": delta_pct}
            if total_gain > best_gain["value"]:
                best_gain = {"name": asset["name"], "value": total_gain}
            performance_data.append({
                "Name": asset["name"],
                "Menge": asset["quantity"],
                "Preis": f"€{latest_close:.2f}",
                "Wert": f"€{latest_close * asset['quantity']:,.2f}",
                "% Anteil": f"{(latest_close * asset['quantity'] / current_value) * 100:.2f}%",
                "Tagesänderung (%)": f"{delta_pct:+.2f}%",
                "Gewinn für dich": f"€{total_gain:+,.2f}"
            })
        else:
            performance_data.append({
                "Name": asset["name"],
                "Menge": asset["quantity"],
                "Preis": "N/A",
                "Wert": "N/A",
                "% Anteil": "N/A",
                "Tagesänderung (%)": "N/A",
                "Gewinn für dich": "N/A"
            })
    
    st.subheader("Tagesperformance")
    if best_pct["name"] and best_gain["name"]:
        st.success(
            f"🏆 Beste Performance: {best_pct['name']} ({best_pct['value']:.2f}%)\n"
            f"💰 Höchster Gewinn: {best_gain['name']} (€{best_gain['value']:+,.2f} für dich)"
        )
    else:
        st.warning("Keine ausreichenden Tagesdaten verfügbar.")

    st.subheader("Detaillierte Positionen")
    st.dataframe(pd.DataFrame(performance_data), use_container_width=True)

if __name__ == "__main__":
    main()