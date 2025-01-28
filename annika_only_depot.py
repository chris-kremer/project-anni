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
data_file = "annika_data.json"

# Load or initialize Annika's ownership and transaction log
def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            data = json.load(f)
            return data["annika"], data["transactions"]
    else:
        # Default ownership for Annika
        annika = {"Percentage": 0.14415851}
        transactions = []
        return annika, transactions


def save_data(annika, transactions):
    with open(data_file, "w") as f:
        json.dump({"annika": annika, "transactions": transactions}, f)


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

        # Fallback for HLBZF
        if ticker == "HLBZF" and (prices[ticker] is None or pd.isna(prices[ticker])):
            prices[ticker] = 133  # Use default value
        if ticker == "POAHF" and (prices[ticker] is None or pd.isna(prices[ticker])):
            prices[ticker] = 33  # Use default value

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


# Recalculate Annika's ownership percentage after a transaction
def recalculate_annika(annika, total_portfolio_value, transaction_amount):
    # Adjust Annika's share value
    current_share_value = total_portfolio_value * (annika["Percentage"] / 100)
    updated_share_value = current_share_value + transaction_amount

    # Update the total portfolio value with the transaction
    new_total_portfolio_value = total_portfolio_value + transaction_amount

    # Recalculate Annika's percentage
    annika["Percentage"] = (updated_share_value / new_total_portfolio_value) * 100
    return annika, new_total_portfolio_value


# Streamlit app
def main():
    annika, transactions = load_data()

    st.title("Annika's Stocks")

    # Fetch prices
    tickers = [asset["Ticker"] for asset in portfolio]
    st.write("Fetching current prices...")
    prices = fetch_current_prices(tickers)

    # Calculate portfolio values
    total_portfolio_value = calculate_portfolio_value(portfolio, prices, initial_cash_position)

    # Display Annika's current share (enlarged and prominent)
    st.subheader("💵 Annika's Current Portfolio Value")
    annika_value = total_portfolio_value * (annika["Percentage"] / 100)
    st.markdown(f"<h1 style='text-align: center; color: green;'>€{annika_value:,.2f}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center;'>Share: {annika['Percentage']:.2f}%</h4>", unsafe_allow_html=True)

    # Add a horizontal rule for spacing
    st.markdown("<hr style='border: 1px solid #ddd;'>", unsafe_allow_html=True)

    # Show table with total value of each position
    st.subheader("📊 Portfolio Overview")
    position_values = []
    for asset in portfolio:
        ticker = asset["Ticker"]
        quantity = asset["Quantity"]
        price = prices.get(ticker, 0)
        total_value = price * quantity if price else 0
        position_values.append({"Ticker": ticker, "Quantity": quantity, "Price (€)": price, "Total Value (€)": total_value})

    position_df = pd.DataFrame(position_values)
    st.table(position_df)

    # Transaction section
    st.subheader("Log an Investment/Withdraw")
    amount = st.number_input("Enter Amount (negative for withdrawal)", value=0.0, step=100.0)
    if st.button("Submit Transaction"):
        # Recalculate Annika's ownership
        annika, total_portfolio_value = recalculate_annika(annika, total_portfolio_value, amount)
        # Log the transaction
        transactions.append({"Amount": amount, "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        save_data(annika, transactions)
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