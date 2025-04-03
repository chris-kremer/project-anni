import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- Configuration ---
st.set_page_config(page_title="Stock Portfolio Tracker", layout="wide")

# --- Portfolio Data ---
portfolio_assets = [
    {"Ticker": "URTH", "Quantity": 480, "Name": "Welt Index"},
    {"Ticker": "WFC", "Quantity": 400, "Name": "Wells Fargo (Bank)"},
    {"Ticker": "HLBZF", "Quantity": 185, "Name": "Heidelberg Materials"},  # OTC
    {"Ticker": "C", "Quantity": 340, "Name": "Citigroup (Bank)"},
    {"Ticker": "BPAQF", "Quantity": 2000, "Name": "British Petroleum (Öl/Gas)"},  # OTC
    {"Ticker": "POAHF", "Quantity": 150, "Name": "Porsche (Auto)"},  # OTC
    {"Ticker": "EXV1.DE", "Quantity": 284, "Name": "Bank Index"},  # Xetra
    {"Ticker": "1COV.DE", "Quantity": 100, "Name": "Covestro (Chemie)"},  # Xetra
    {"Ticker": "SPY", "Quantity": 10, "Name": "USA Index"},
    {"Ticker": "HYMTF", "Quantity": 100, "Name": "Hyundai (Auto)"},  # OTC
    {"Ticker": "SHEL", "Quantity": 75, "Name": "Shell (Öl/Gas)"},
    {"Ticker": "DAX", "Quantity": 0.0114, "Name": "Deutschland Index"},  # ^GDAXI is the YF ticker
    {"Ticker": "PLTR", "Quantity": 100, "Name": "Palantir (Rüstung Software)"},
    {"Ticker": "UQ2B.DU", "Quantity": 5, "Name": "Europa Index"},  # Dusseldorf
    {"Ticker": "DB", "Quantity": 1, "Name": "Deutsche Bank"},
    {"Ticker": "GS", "Quantity": 9, "Name": "Goldman Sachs (Bank)"},
    {"Ticker": "MBG.DE", "Quantity": 50, "Name": "Mercedes (Auto)"},  # Xetra
]

initial_cash = 17000.00

# --- Ownership Percentages ---
# (Interpreted as percentages -> to be converted to decimal fractions)
annika_pct   = 0.343225979   # 0.343225979 percent → 0.00343225979 fraction if truly "percent"
christian_pct = 31.196773489 # 31.196773489 percent → 0.31196773489 fraction
parents_pct   = 69.713319    # 69.713319 percent   → 0.69713319 fraction

# Convert these “percent” values to decimals if they are indeed meant as percentages
annika_fraction    = annika_pct / 100.0
christian_fraction = christian_pct / 100.0
parents_fraction   = parents_pct / 100.0

# --- Helper Functions ---
@st.cache_data(ttl=600)
def get_stock_data(tickers):
    """
    Fetches current price data for a list of tickers using yfinance.
    Handles potential issues with indices vs. stocks.
    Returns a dictionary mapping tickers to their current prices.
    """
    data = {}
    ticker_objects = yf.Tickers(tickers)
    for ticker in tickers:
        try:
            info = ticker_objects.tickers[ticker].info
            price = (info.get('currentPrice')
                     or info.get('regularMarketPrice')
                     or info.get('previousClose'))
            if price:
                data[ticker] = price
            else:
                hist = ticker_objects.tickers[ticker].history(period='2d')
                if not hist.empty:
                    data[ticker] = hist['Close'].iloc[-1]
                else:
                    st.warning(f"Could not find price data for {ticker}. Info: {info}")
                    data[ticker] = None
        except Exception as e:
            st.error(f"Error fetching data for {ticker}: {e}")
            data[ticker] = None
    return data

# --- Main Application Logic ---
st.title("📈 My Stock Portfolio Tracker")
st.markdown(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

df = pd.DataFrame(portfolio_assets)

# Correct common index tickers if needed
ticker_mapping = {
    "DAX": "^GDAXI"
    # e.g.: "DB": "DBK.DE" if you want Xetra listing, etc.
}
df['yf_Ticker'] = df['Ticker'].replace(ticker_mapping)

# Fetch prices (remove the "Fetching..." and "Success" messages)
tickers_to_fetch = df['yf_Ticker'].unique().tolist()
current_prices = get_stock_data(tickers_to_fetch)

# Map prices back to the DataFrame
df['Current Price'] = df['yf_Ticker'].map(current_prices)
df['Current Price'] = pd.to_numeric(df['Current Price'], errors='coerce')
df['Current Value'] = df['Current Price'] * df['Quantity']
df['Current Value'] = df['Current Value'].fillna(0)

# Check for missing
missing_prices = df[df['Current Price'].isna()]['Ticker'].tolist()
if missing_prices:
    st.warning(f"Could not fetch current price for: {', '.join(missing_prices)}. Excluded from totals.")

# Calculate totals
total_stock_value = df['Current Value'].sum()
total_portfolio_value = total_stock_value + initial_cash

# --- Display Portfolio ---
st.header("Portfolio Summary")

# We only show two metrics (removing Cash Balance)
col1, col2 = st.columns(2)
col1.metric("Total Portfolio Value", f"€{total_portfolio_value:,.2f}")
col2.metric("Total Stock Value", f"€{total_stock_value:,.2f}")

# --- Ownership Breakdown ---
st.header("Ownership Breakdown")
annika_value = total_portfolio_value * annika_fraction
christian_value = total_portfolio_value * christian_fraction
parents_value = total_portfolio_value * parents_fraction

col_a, col_b, col_c = st.columns(3)
col_a.metric("Annika’s Value", f"€{annika_value:,.2f}")
col_b.metric("Christian’s Value", f"€{christian_value:,.2f}")
col_c.metric("Parents’ Value", f"€{parents_value:,.2f}")

st.header("Asset Details")

df_display = df[['Ticker', 'Name', 'Quantity', 'Current Price', 'Current Value']].copy()
df_display['Current Price'] = df_display['Current Price'].map('€{:,.2f}'.format, na_action='ignore')
df_display['Current Value'] = df_display['Current Value'].map('€{:,.2f}'.format)

st.dataframe(df_display, hide_index=True, use_container_width=True)

# Uncomment below if you want to see raw fetched data
# with st.expander("Raw Ticker Data"):
#     st.write(current_prices)