# streamlit_app.py
import yfinance as yf
import pandas as pd
import streamlit as st

# Define portfolio
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

cash_position = 17000  # Cash position in USD


def fetch_current_prices(tickers):
    """Fetch current prices for a list of tickers."""
    prices = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period='1d')
            if not data.empty and 'Close' in data.columns:
                current_price = data['Close'].iloc[-1]
                prices[ticker] = current_price
            else:
                prices[ticker] = None
        except Exception as e:
            prices[ticker] = None
    return prices


def calculate_portfolio_value(portfolio, prices, cash):
    """Calculate total portfolio value."""
    total_value = cash
    portfolio_data = []
    for asset in portfolio:
        ticker = asset["Ticker"]
        quantity = asset["Quantity"]
        price = prices.get(ticker)
        if price is not None:
            value = price * quantity
            total_value += value
            portfolio_data.append({"Ticker": ticker, "Quantity": quantity, "Price": price, "Value": value})
        else:
            portfolio_data.append({"Ticker": ticker, "Quantity": quantity, "Price": "N/A", "Value": "N/A"})
    return total_value, portfolio_data


def main():
    """Streamlit app main function."""
    st.title("Investment Portfolio Performance")

    # Fetch prices
    tickers = [asset["Ticker"] for asset in portfolio]
    st.write("Fetching current prices...")
    prices = fetch_current_prices(tickers)

    # Calculate values
    total_value, portfolio_data = calculate_portfolio_value(portfolio, prices, cash_position)

    # Display portfolio table
    st.subheader("Portfolio Overview")
    df = pd.DataFrame(portfolio_data)
    st.table(df)

    # Display total value
    st.subheader("Total Portfolio Value")
    st.write(f"💰 **{total_value:,.2f} USD**")

    # Annika Anteil Calculation
    percentage = 0.141974937637508 / 100
    annika_share = total_value * percentage
    st.subheader("Annika Anteil")
    st.write(f"👩‍💼 **{annika_share:,.2f} EUR**")


if __name__ == "__main__":
    main()