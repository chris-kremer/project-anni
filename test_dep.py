import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- Configuration ---
st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide")

# --- Portfolio Data ---
# Your portfolio assets as provided
portfolio_assets = [
    {"Ticker": "URTH", "Quantity": 480, "Name": "Welt Index"},
    {"Ticker": "WFC", "Quantity": 400, "Name": "Wells Fargo (Bank)"},
    {"Ticker": "HLBZF", "Quantity": 185, "Name": "Heidelberg Materials"}, # Note: OTC tickers like HLBZF might have delayed or less frequent data
    {"Ticker": "C", "Quantity": 340, "Name": "Citigroup (Bank)"},
    {"Ticker": "BPAQF", "Quantity": 2000, "Name": "British Petroleum (Öl/Gas)"}, # Note: OTC ticker
    {"Ticker": "POAHF", "Quantity": 150, "Name": "Porsche (Auto)"}, # Note: OTC ticker
    {"Ticker": "EXV1.DE", "Quantity": 284, "Name": "Bank Index"}, # Xetra ticker
    {"Ticker": "1COV.DE", "Quantity": 100, "Name": "Covestro (Chemie)"}, # Xetra ticker
    {"Ticker": "SPY", "Quantity": 10, "Name": "USA Index"},
    {"Ticker": "HYMTF", "Quantity": 100, "Name": "Hyundai (Auto)"}, # Note: OTC ticker
    {"Ticker": "SHEL", "Quantity": 75, "Name": "Shell (Öl/Gas)"}, # Assumes primary listing (e.g., NYSE/LSE)
    {"Ticker": "DAX", "Quantity": 6, "Name": "Deutschaland Index"}, # Note: ^GDAXI is the common Yahoo Finance ticker for DAX index
    {"Ticker": "PLTR", "Quantity": 100, "Name": "Palantir (Rüstung Software)"},
    {"Ticker": "UQ2B.DU", "Quantity": 5, "Name": "Europa Index"}, # Dusseldorf ticker
    {"Ticker": "DB", "Quantity": 1, "Name": "Deutsche Bank"}, # Assumes primary listing (e.g., NYSE) - Use DBK.DE for Xetra
    {"Ticker": "GS", "Quantity": 9, "Name": "Goldman Sachs (Bank)"},
    {"Ticker": "MBG.DE", "Quantity": 50, "Name": "Mercedes (Auto)"}, # Xetra ticker
]

initial_cash = 17000.00 # Make it a float for calculations

# --- Helper Functions ---

# Use Streamlit's caching to avoid re-fetching data on every interaction
@st.cache_data(ttl=600) # Cache data for 600 seconds (10 minutes)
def get_stock_data(tickers):
    """
    Fetches current price data for a list of tickers using yfinance.
    Handles potential issues with indices vs stocks.
    Returns a dictionary mapping tickers to their current prices.
    """
    data = {}
    ticker_objects = yf.Tickers(tickers) # Efficiently fetch data for multiple tickers

    for ticker in tickers:
        try:
            info = ticker_objects.tickers[ticker].info

            # Different fields might hold the 'current' price
            # Indices often use 'previousClose' or 'regularMarketPrice' if market is open
            # Stocks often use 'currentPrice' or 'regularMarketPrice'
            price = info.get('currentPrice') or \
                    info.get('regularMarketPrice') or \
                    info.get('previousClose') # Fallback

            if price:
                data[ticker] = price
            else:
                # If still no price, try fetching history (useful for indices)
                hist = ticker_objects.tickers[ticker].history(period='2d') # Get last 2 days
                if not hist.empty:
                    data[ticker] = hist['Close'].iloc[-1] # Use the last closing price
                else:
                     st.warning(f"Could not find price data for {ticker}. Info: {info}")
                     data[ticker] = None # Mark as not found

        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {e}")
            data[ticker] = None # Mark as error / not found
    return data

# --- Main Application Logic ---

st.title("📈 My Stock Portfolio Tracker")
st.markdown(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Convert portfolio list to DataFrame
df = pd.DataFrame(portfolio_assets)

# Correct common index tickers for Yahoo Finance if needed
# Example: DAX index is usually ^GDAXI on Yahoo Finance
ticker_mapping = {
    "DAX": "^GDAXI"
    # Add other mappings if necessary (e.g., if DB should be DBK.DE)
    #"DB": "DBK.DE" # Uncomment if you prefer the Xetra listing for Deutsche Bank
}
df['yf_Ticker'] = df['Ticker'].replace(ticker_mapping)


# Get the list of tickers to fetch
tickers_to_fetch = df['yf_Ticker'].unique().tolist()

# Fetch the current prices
st.info("Fetching latest stock data...")
current_prices = get_stock_data(tickers_to_fetch)
st.success("Stock data fetched successfully!")

# Map prices back to the DataFrame
df['Current Price'] = df['yf_Ticker'].map(current_prices)

# Handle cases where price fetching failed
df['Current Price'] = pd.to_numeric(df['Current Price'], errors='coerce') # Ensure prices are numeric, turn errors into NaN
missing_prices = df[df['Current Price'].isna()]['Ticker'].tolist()
if missing_prices:
    st.warning(f"Could not fetch current price for: {', '.join(missing_prices)}. Their value will be excluded from totals.")

# Calculate current value for each asset
df['Current Value'] = df['Current Price'] * df['Quantity']
df['Current Value'] = df['Current Value'].fillna(0) # Treat missing values as 0 for summation

# Calculate totals
total_stock_value = df['Current Value'].sum()
total_portfolio_value = total_stock_value + initial_cash

# --- Display Portfolio ---

st.header("Portfolio Summary")

# Use columns for better layout
col1, col2, col3 = st.columns(3)
col1.metric("Total Portfolio Value", f"€{total_portfolio_value:,.2f}")
col2.metric("Total Stock Value", f"€{total_stock_value:,.2f}")
col3.metric("Cash Balance", f"€{initial_cash:,.2f}")

st.header("Asset Details")

# Format the DataFrame for display
df_display = df[['Ticker', 'Name', 'Quantity', 'Current Price', 'Current Value']].copy()
df_display['Current Price'] = df_display['Current Price'].map('€{:,.2f}'.format, na_action='ignore')
df_display['Current Value'] = df_display['Current Value'].map('€{:,.2f}'.format)


# Display the DataFrame without the index
st.dataframe(df_display, hide_index=True, use_container_width=True)

# Optional: Display raw fetched data for debugging
# with st.expander("Raw Ticker Data"):
#    st.write(current_prices)