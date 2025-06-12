import yfinance as yf
import pandas as pd
import streamlit as st
import json
import os

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
    "ownership": {
        "Annika": 0.181639346,
        "Parents": 67.821735319,
        "Christian": 31.996773489,
    },
}


def load_config(path: str = CONFIG_FILE):
    """Load portfolio configuration from JSON file."""
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG


config = load_config()
portfolio = config.get("portfolio", DEFAULT_CONFIG["portfolio"])
initial_cash_position = config.get("initial_cash", DEFAULT_CONFIG["initial_cash"])
data_file = "portfolio_data.json"

# Load or initialize ownership and transaction log
def load_data():
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            data = json.load(f)
            return data["ownership"], data["transactions"]
    else:
        # Default ownership
        ownership = {
            "Annika": {"Percentage": 0.14415851},
            "Parents": {"Percentage": 66.4},
            "Christian": {"Percentage": 33.6 - 0.14415851},
        }
        transactions = []
        return ownership, transactions


def save_data(ownership, transactions):
    with open(data_file, "w") as f:
        json.dump({"ownership": ownership, "transactions": transactions}, f)


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
    portfolio_data = []
    for asset in portfolio:
        ticker = asset["Ticker"]
        quantity = asset["Quantity"]
        price = prices.get(ticker)
        if price:
            value = price * quantity
            total_value += value
            portfolio_data.append({"Ticker": ticker, "Quantity": quantity, "Price": price, "Value": value})
        else:
            portfolio_data.append({"Ticker": ticker, "Quantity": quantity, "Price": "N/A", "Value": "N/A"})
    return total_value, portfolio_data


# Recalculate ownership percentages after a transaction
def recalculate_ownership(ownership, total_portfolio_value, transaction_amount, person):
    # Adjust the specific person's value
    current_share_value = total_portfolio_value * (ownership[person]["Percentage"] / 100)
    updated_share_value = current_share_value + transaction_amount

    # Update the total portfolio value with the transaction
    new_total_portfolio_value = total_portfolio_value + transaction_amount

    # Recalculate percentages for all participants
    for p in ownership:
        if p == person:
            ownership[p]["Percentage"] = (updated_share_value / new_total_portfolio_value) * 100
        else:
            current_share_value = total_portfolio_value * (ownership[p]["Percentage"] / 100)
            ownership[p]["Percentage"] = (current_share_value / new_total_portfolio_value) * 100

    return ownership


# Streamlit app
def main():
    ownership, transactions = load_data()

    st.title("Investment Portfolio Performance")

    # Fetch prices
    tickers = [asset["Ticker"] for asset in portfolio]
    st.write("Fetching current prices...")
    prices = fetch_current_prices(tickers)

    # Calculate portfolio values
    total_portfolio_value, portfolio_data = calculate_portfolio_value(portfolio, prices, initial_cash_position)

    # Display portfolio table
    st.subheader("Portfolio Overview")
    df = pd.DataFrame(portfolio_data)
    st.table(df)

    # Display individual balances
    st.subheader("Individual Balances and Ownership")
    for person, data in ownership.items():
        individual_value = total_portfolio_value * (data["Percentage"] / 100)
        st.write(f"**{person}**: 💰 {individual_value:,.2f} EUR, Share: {data['Percentage']:.2f}%")

    # Withdrawal/Investment section
    st.subheader("Make a Transaction")
    person = st.selectbox("Select Participant", ownership.keys())
    amount = st.number_input("Enter Amount (negative for withdrawal)", value=0.0, step=100.0)
    if st.button("Submit Transaction"):
        if person in ownership:
            # Recalculate ownership after the transaction
            ownership = recalculate_ownership(ownership, total_portfolio_value, amount, person)
            # Update the transaction log
            transactions.append({"Person": person, "Amount": amount})
            save_data(ownership, transactions)
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