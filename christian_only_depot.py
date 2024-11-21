import yfinance as yf
import pandas as pd
import streamlit as st
import json
import os
from datetime import datetime

# Initial portfolio and ownership
portfolio = [
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

initial_cash_position = 17000
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


def calculate_monthly_christian_share(portfolio, historical_prices, christian, initial_cash):
    """
    Calculates the total value of Christian's share for each month based on historical prices.
    """
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
        # Calculate Christian's share
        christian_value = total_value * (christian["Percentage"] / 100)
        if christian_value >= 30000:  # Filter out values below 30k
            monthly_values.append({"Date": date, "Christians Share": christian_value})

    return pd.DataFrame(monthly_values)


def calculate_annual_returns(dataframe):
    """
    Calculates annual percentage returns based on Christian's share, but only for full years.
    """
    # Extract the year and month from the dates
    dataframe["Year"] = dataframe["Date"].dt.year
    dataframe["Month"] = dataframe["Date"].dt.month

    # Group by year and aggregate data
    annual_data = dataframe.groupby("Year").agg(
        first_value=("Christians Share", "first"),
        last_value=("Christians Share", "last"),
        months_covered=("Month", "nunique")
    )

    # Identify full years (12 months) and the current year (up to now)
    current_year = datetime.now().year
    annual_data = annual_data[
        (annual_data["months_covered"] == 12) |  # Full year
        ((annual_data.index == current_year) & (annual_data["months_covered"] > 0))  # Current year
    ]

    # Calculate annual returns
    annual_data["Annual Return (%)"] = ((annual_data["last_value"] - annual_data["first_value"]) / annual_data["first_value"]) * 100

    return annual_data.reset_index()[["Year", "Annual Return (%)"]]


def main():
    christian, transactions = load_data()

    st.title("Christian's Stocks")

    # Fetch prices
    tickers = [asset["Ticker"] for asset in portfolio]
    st.write("Fetching historical prices...")
    historical_prices = fetch_historical_prices(tickers)

    # Calculate monthly Christian's share
    monthly_christian_share = calculate_monthly_christian_share(
        portfolio, historical_prices, christian, initial_cash_position
    )

    # Display Christian's share chart
    st.subheader("📈 Christian's Share Over the Last 2 Years")
    if not monthly_christian_share.empty:
        st.line_chart(monthly_christian_share.set_index("Date")["Christians Share"])
    else:
        st.write("No data available above the threshold of €30,000.")

    # Calculate annual returns
    if not monthly_christian_share.empty:
        annual_returns = calculate_annual_returns(monthly_christian_share)

    # Display annual returns table
    st.subheader("📊 Annual Percentage Returns")
    if not monthly_christian_share.empty:
        st.table(annual_returns)
    else:
        st.write("No annual return data available.")

if __name__ == "__main__":
    main()