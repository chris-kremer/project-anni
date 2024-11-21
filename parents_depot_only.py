import yfinance as yf
import pandas as pd
import streamlit as st
import json
import os

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

initial_cash = 17000
data_file_path = "parents_data.json"

# Load ownership data
def load_ownership_data():
    if os.path.exists(data_file_path):
        try:
            with open(data_file_path, "r") as file:
                data = json.load(file)
                return data.get("ownership", {"Percentage": 66.5})
        except json.JSONDecodeError:
            st.warning("Data file is corrupt. Using default values.")
            return {"Percentage": 66.5}
    else:
        return {"Percentage": 66.5}

# Calculate current asset values
def calculate_asset_values(portfolio):
    asset_values = []
    for asset in portfolio:
        try:
            ticker = asset["Ticker"]
            quantity = asset["Quantity"]
            stock = yf.Ticker(ticker)
            price = stock.history(period="1d")["Close"].iloc[-1]
            value = price * quantity
            asset_values.append({"Ticker": ticker, "Quantity": quantity, "Price (€)": round(price, 2), "Value (€)": round(value, 2)})
        except Exception as e:
            st.warning(f"Error fetching price for {ticker}: {e}")
            asset_values.append({"Ticker": ticker, "Quantity": quantity, "Price (€)": "N/A", "Value (€)": "N/A"})
    return pd.DataFrame(asset_values)

# Calculate current share value
def calculate_current_share_value(asset_values, ownership_data, cash):
    total_portfolio_value = cash + asset_values["Value (€)"].sum()
    share_value = total_portfolio_value * (ownership_data["Percentage"] / 100)
    return share_value

# Calculate return percentage
def calculate_return_percentage(current_value, baseline=107000):
    return ((current_value / baseline)-1) * 100

def main():
    st.title("Aktueller Wert eurer Aktien:")

    # Load ownership data
    ownership = load_ownership_data()

    # Calculate asset values
    asset_values_df = calculate_asset_values(portfolio_assets)

    # Calculate current share value
    current_share_value = calculate_current_share_value(asset_values_df, ownership, initial_cash)

    # Calculate return percentage
    return_percentage = calculate_return_percentage(current_share_value)

    # Display the current share value
    st.metric(label="", value=f"{current_share_value:,.2f} €")

    # Display the return percentage
    st.markdown(
        f"<p style='font-size:20px; color:green;'>+ {return_percentage:.2f}%</p>",
        unsafe_allow_html=True,
    )

if __name__ == "__main__":
    main()