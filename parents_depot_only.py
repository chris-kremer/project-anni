import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime
import pytz
import os
import json

# Initial portfolio and ownership
portfolio_assets = [
    {"Ticker": "URTH", "Quantity": 480},
    {"Ticker": "WFC", "Quantity": 400},
    {"Ticker": "HLBZF", "Quantity": 185},
    {"Ticker": "C", "Quantity": 340},
    {"Ticker": "BPAQF", "Quantity": 2000},
    {"Ticker": "POAHF", "Quantity": 150},
    {"Ticker": "EXV1.DE", "Quantity": 284},
    {"Ticker": "1COV.DE", "Quantity": 100},
    {"Ticker": "SPY", "Quantity": 10},
    {"Ticker": "HYMTF", "Quantity": 100},
    {"Ticker": "SHEL", "Quantity": 75},
    {"Ticker": "DAX", "Quantity": 6},
    {"Ticker": "PLTR", "Quantity": 100},
    {"Ticker": "UQ2B.DU", "Quantity": 5},
    {"Ticker": "DB", "Quantity": 1},
    {"Ticker": "GS", "Quantity": 9},
    {"Ticker": "MBG.DE", "Quantity": 50},
]

initial_cash = 42000
data_file_path = "parents_data.json"
local_tz = pytz.timezone("Europe/Berlin")  # Local timezone

# Load ownership data
def load_ownership_data():
    if os.path.exists(data_file_path):
        try:
            with open(data_file_path, "r") as file:
                data = json.load(file)
                return data.get("ownership", {"Percentage": 69.821735319})
        except json.JSONDecodeError:
            st.warning("Data file is corrupt. Using default values.")
            return {"Percentage": 69.821735319}
    else:
        return {"Percentage": 69.821735319}

# Fetch historical prices
def fetch_historical_prices(tickers):
    """
    Fetches monthly historical prices for the last 2 years for a list of tickers.
    """
    historical_prices = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            # Fetch data for the last 2 years
            data = stock.history(period="2y", interval="1mo")
            if not data.empty:
                historical_prices[ticker] = data["Close"].fillna(method="ffill")
            else:
                historical_prices[ticker] = None
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            historical_prices[ticker] = None
    return historical_prices

# Calculate monthly share value
def calculate_monthly_share_value(portfolio, historical_prices, ownership, initial_cash):
    all_dates = set()
    for prices in historical_prices.values():
        if prices is not None:
            all_dates.update(prices.index)
    all_dates = sorted(all_dates)

    monthly_values = []
    for date in all_dates:
        total_value = initial_cash
        for asset in portfolio:
            ticker = asset["Ticker"]
            quantity = asset["Quantity"]
            prices = historical_prices.get(ticker)
            if prices is not None and date in prices:
                price = prices.loc[date]
                if pd.isna(price) or price <= 0:
                    continue
                total_value += price * quantity
        # Calculate share value
        share_value = total_value * (ownership["Percentage"] / 100)
        if share_value >= 50000:  # Filter out values below 30k
            monthly_values.append({"Date": date, "Share Value": share_value})

    return pd.DataFrame(monthly_values)

# Calculate current share value
def calculate_current_value(portfolio, ownership, initial_cash, historical_prices):
    total_value = initial_cash
    for asset in portfolio:
        ticker = asset["Ticker"]
        quantity = asset["Quantity"]
        prices = historical_prices.get(ticker)
        if prices is not None and not prices.empty:
            current_price = prices.iloc[-1]
            if pd.notna(current_price) and current_price > 0:
                total_value += current_price * quantity
    share_value = total_value * (ownership["Percentage"] / 100)
    return share_value


def main():
    st.title("Depot Anteil")

    # Load ownership data
    ownership = load_ownership_data()

    # Fetch historical prices
    tickers = [asset["Ticker"] for asset in portfolio_assets]
    historical_prices = fetch_historical_prices(tickers)

    # Calculate current share value
    current_value = calculate_current_value(portfolio_assets, ownership, initial_cash, historical_prices)
    st.metric(
        label="Aktueller Wert",
        value=f"€{current_value:,.2f}",
        delta=f"{((current_value / 117000) - 1) * 100:.2f}%",
        delta_color="normal"
    )
    
    # Calculate monthly share value
    monthly_share_value = calculate_monthly_share_value(
        portfolio_assets, historical_prices, ownership, initial_cash
    )

    # Add current value as a datapoint
    current_date = pd.Timestamp.now()
    if monthly_share_value.empty:
        monthly_share_value = pd.DataFrame([{"Date": current_date, "Share Value": current_value}])
    else:
        monthly_share_value = pd.concat(
            [monthly_share_value, pd.DataFrame([{"Date": current_date, "Share Value": current_value}])],
            ignore_index=True
        )

    # Display parents' share chart
    st.subheader("Wertentwicklung über die letzten 2 Jahre")
    if not monthly_share_value.empty:
        st.line_chart(monthly_share_value.set_index("Date")["Share Value"])
    else:
        st.write("No data available above the threshold of €30,000.")

if __name__ == "__main__":
    main()
