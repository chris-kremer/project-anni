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
        with open(data_file, "r") as f:
            data = json.load(f)
            return data["christian"], data["transactions"]
    else:
        # Default ownership for Christian
        christian = {"Percentage": 0.15000000}
        transactions = []
        return christian, transactions


def save_data(christian, transactions):
    with open(data_file, "w") as f:
        json.dump({"christian": christian, "transactions": transactions}, f)


# Fetch current prices
def fetch_current_prices(tickers):
    prices = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d")
            if not data.empty and "Close" in data.columns:
                prices[ticker] = data["Close"].iloc[-1]
            else:
                prices[ticker] = None
        except Exception:
            prices[ticker] = None
    return prices


# Calculate portfolio value
def calculate_portfolio_value(portfolio, prices, cash):
    total_value = cash
    for asset in portfolio:
        ticker = asset["Ticker"]
        quantity = asset["Quantity"]
        price = prices.get(ticker)
        if price:
            total_value += price * quantity
    return total_value


# Recalculate Christian's ownership percentage after a transaction
def recalculate_christian(christian, total_portfolio_value, transaction_amount):
    # Adjust Christian's share value
    current_share_value = total_portfolio_value * (christian["Percentage"] / 100)
    updated_share_value = current_share_value + transaction_amount

    # Update the total portfolio value with the transaction
    new_total_portfolio_value = total_portfolio_value + transaction_amount

    # Recalculate Christian's percentage
    christian["Percentage"] = (updated_share_value / new_total_portfolio_value) * 100
    return christian, new_total_portfolio_value


# Streamlit app
def main():
    christian, transactions = load_data()

    st.title("Christian's Stocks")

    # Fetch prices
    tickers = [asset["Ticker"] for asset in portfolio]
    st.write("Fetching current prices...")
    prices = fetch_current_prices(tickers)

    # Calculate portfolio values
    total_portfolio_value = calculate_portfolio_value(portfolio, prices, initial_cash_position)

    # Display Christian's current share (enlarged and prominent)
    st.subheader("💵 Christian's Current Portfolio Value")
    christian_value = total_portfolio_value * (christian["Percentage"] / 100)
    st.markdown(f"<h1 style='text-align: center; color: green;'>€{christian_value:,.2f}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center;'>Share: {christian['Percentage']:.2f}%</h4>", unsafe_allow_html=True)

    # Add a horizontal rule for spacing
    st.markdown("<hr style='border: 1px solid #ddd;'>", unsafe_allow_html=True)

    # Transaction section
    st.subheader("Log an Investment/Withdraw")
    amount = st.number_input("Enter Amount (negative for withdrawal)", value=0.0, step=100.0)
    if st.button("Submit Transaction"):
        # Recalculate Christian's ownership
        christian, total_portfolio_value = recalculate_christian(christian, total_portfolio_value, amount)
        # Log the transaction
        transactions.append({"Amount": amount, "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        save_data(christian, transactions)
        st.success("Transaction processed successfully!")

    # Transaction log
    st.subheader("Transaction Log")
    if transactions:
        log_df = pd.DataFrame(transactions)
        st.table(log_df)
    else:
        st.write("No transactions logged yet.")


if __name__ == "__main__":
    main()