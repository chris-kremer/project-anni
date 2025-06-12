import yfinance as yf
import pandas as pd
import streamlit as st
import json
import os
from datetime import datetime

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "initial_cash": 17000,
    "portfolio": [
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
    ],
}


def load_config(path: str = CONFIG_FILE):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG

# Initial portfolio and cash loaded from configuration
config = load_config()
portfolio = config.get("portfolio", DEFAULT_CONFIG["portfolio"])
initial_cash_position = config.get("initial_cash", DEFAULT_CONFIG["initial_cash"])
data_file = "christian_data.json"

# Load or initialize Christian's ownership and transaction log
def load_data():
    if os.path.exists(data_file):
        try:
            with open(data_file, "r") as f:
                data = json.load(f)
                return data.get("christian", {"Percentage": 0.15000000}), data.get("transactions", [])
        except json.JSONDecodeError:
            st.warning("Data file is corrupt. Reinitializing.")
            return {"Percentage": 0.15000000}, []
    else:
        christian = {"Percentage": 0.15000000}
        transactions = []
        return christian, transactions


def save_data(christian, transactions):
    with open(data_file, "w") as f:
        json.dump({"christian": christian, "transactions": transactions}, f)


# Fetch historical prices
def fetch_historical_prices(tickers):
    historical_prices = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="2y", interval="1mo")
            if not data.empty:
                historical_prices[ticker] = data["Close"].fillna(method="ffill")
            else:
                historical_prices[ticker] = None
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            historical_prices[ticker] = None
    return historical_prices


def calculate_current_value(portfolio, christian, initial_cash, historical_prices):
    total_value = initial_cash
    for asset in portfolio:
        ticker = asset["Ticker"]
        quantity = asset["Quantity"]
        prices = historical_prices.get(ticker)
        if prices is not None and not prices.empty:
            current_price = prices.iloc[-1]
            if pd.notna(current_price) and current_price > 0:
                total_value += current_price * quantity
    christian_value = total_value * (christian["Percentage"] / 100)
    return christian_value


def calculate_monthly_christian_share(portfolio, historical_prices, christian, initial_cash):
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
        christian_value = total_value * (christian["Percentage"] / 100)
        if christian_value >= 30000:  # Filter out values below 30k
            monthly_values.append({"Date": date, "Christians Share": christian_value})

    return pd.DataFrame(monthly_values)


def main():
    christian, transactions = load_data()

    st.title("Christian's Stocks")

    tickers = [asset["Ticker"] for asset in portfolio]
    historical_prices = fetch_historical_prices(tickers)

    current_value = calculate_current_value(portfolio, christian, initial_cash_position, historical_prices)
    st.metric(
        label="Current Value of Christian's Share",
        value=f"€{current_value:,.2f}",
        delta=f"{((current_value / 32000) - 1) * 100:.2f}%",
        delta_color="normal"
    )

    # Calculate monthly Christian's share
    monthly_christian_share = calculate_monthly_christian_share(
        portfolio, historical_prices, christian, initial_cash_position
    )

    # Add current value as a datapoint
    current_date = pd.Timestamp.now()
    if monthly_christian_share.empty:
        monthly_christian_share = pd.DataFrame([{"Date": current_date, "Christians Share": current_value}])
    else:
        monthly_christian_share = pd.concat(
            [monthly_christian_share, pd.DataFrame([{"Date": current_date, "Christians Share": current_value}])],
            ignore_index=True
        )

    # Display Christian's share chart
    st.subheader("Christian's Share Over the Last 2 Years")
    if not monthly_christian_share.empty:
        st.line_chart(monthly_christian_share.set_index("Date")["Christians Share"])
    else:
        st.write("No data available above the threshold of €30,000.")


if __name__ == "__main__":
    main()