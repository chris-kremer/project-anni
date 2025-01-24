import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
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
local_tz = pytz.timezone("Europe/Berlin")

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

def fetch_historical_prices(tickers):
    historical_prices = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="2y", interval="1mo")
            if not data.empty:
                # Fixed deprecated fillna method
                historical_prices[ticker] = data["Close"].ffill()
            else:
                historical_prices[ticker] = None
        except Exception as e:
            print(f"Error fetching historical data for {ticker}: {e}")
            historical_prices[ticker] = None
    return historical_prices


def calculate_value(portfolio, price_dict, initial_cash, ownership):
    total_value = initial_cash
    for asset in portfolio:
        ticker = asset["Ticker"]
        quantity = asset["Quantity"]
        price = price_dict.get(ticker)
        if price is not None and pd.notna(price) and price > 0:
            total_value += price * quantity
    return total_value * (ownership["Percentage"] / 100)

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
        share_value = total_value * (ownership["Percentage"] / 100)
        if share_value >= 50000:
            monthly_values.append({"Date": date, "Share Value": share_value})

    return pd.DataFrame(monthly_values)
def fetch_daily_prices(tickers):
    daily_prices = {}
    for ticker in tickers:
        try:
            data = yf.download(ticker, period="5d", interval="1d", progress=False)
            if not data.empty:
                # Fix timezone handling: Localize to UTC first, then convert to local
                data.index = data.index.tz_localize('UTC').tz_convert(local_tz)
                daily_prices[ticker] = data
            else:
                daily_prices[ticker] = None
        except Exception as e:
            print(f"Error fetching daily data for {ticker}: {e}")
            daily_prices[ticker] = None
    return daily_prices

def main():
    st.title("Depot Anteil")
    ownership = load_ownership_data()

    # Fetch prices
    tickers = [asset["Ticker"] for asset in portfolio_assets]
    historical_prices = fetch_historical_prices(tickers)
    daily_prices = fetch_daily_prices(tickers)

    # Calculate values
    current_date = datetime.now(local_tz).date()
    
    # Yesterday's open value
    yesterday_open_dict = {}
    for ticker in tickers:
        data = daily_prices.get(ticker)
        if data is not None and not data.empty:
            # Already converted to local timezone in fetch_daily_prices
            before_today = data[data.index.date < current_date]
            if not before_today.empty:
                yesterday_open_dict[ticker] = before_today.iloc[-1]["Open"]

    # Current value calculation
    current_price_dict = {}
    for ticker in tickers:
        data = daily_prices.get(ticker)
        if data is not None and not data.empty:
            current_price_dict[ticker] = data.iloc[-1]["Close"]

    current_value = calculate_value(portfolio_assets, current_price_dict, initial_cash, ownership)
    total_portfolio_value = sum(
        price * asset["Quantity"] for asset, price in zip(portfolio_assets, current_price_dict.values())
    ) + initial_cash

    # Verify ownership percentage
    ownership_percentage = current_value / (total_portfolio_value * (ownership["Percentage"] / 100)) * 100
  

    # Display metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Aktueller Wert",
            value=f"€{current_value:,.2f}",
            delta=f"{((current_value / 130000) - 1) * 100:.2f}% ",
            delta_color="normal"
        )
    
    with col2:
        if yesterday_open_dict:
            yesterday_value = calculate_value(portfolio_assets, yesterday_open_dict, initial_cash, ownership)
            delta_value = current_value - yesterday_value
            delta_percent = (delta_value / yesterday_value) * 100
            st.metric(
                label="Seit gestern",
                value=f"€{delta_value:+,.2f}",
                delta=f"{delta_percent:+.2f}%",
                delta_color="inverse"
            )
        else:
            st.metric("Seit gestern Open", "N/A")

    # Chart handling with proper timezones
    st.subheader("Wertentwicklung über die letzten 2 Jahre")
    monthly_share_value = calculate_monthly_share_value(
        portfolio_assets, historical_prices, ownership, initial_cash
    )

    if not monthly_share_value.empty:
        # Ensure all dates are tz-aware
        monthly_share_value["Date"] = monthly_share_value["Date"].dt.tz_convert(local_tz)
        
        # Add current value with proper tz-aware timestamp
        current_ts = pd.Timestamp.now(tz=local_tz)
        last_date = monthly_share_value["Date"].iloc[-1]
        
        if current_ts > last_date:
            new_entry = pd.DataFrame([{
                "Date": current_ts,
                "Share Value": current_value
            }])
            monthly_share_value = pd.concat(
                [monthly_share_value, new_entry],
                ignore_index=True
            )

        st.line_chart(
            monthly_share_value.set_index("Date")["Share Value"],
            use_container_width=True
        )
    else:
        st.write("Keine Daten über dem Schwellenwert von €50.000 verfügbar.")

    # Debug table at bottom
    st.subheader("Detaillierte Aktienpositionen")
    debug_data = []
    for asset in portfolio_assets:
        ticker = asset["Ticker"]
        data = daily_prices.get(ticker)
        if data is not None and not data.empty:
            price = data.iloc[-1]["Close"]
            value = price * asset["Quantity"]
            debug_data.append({
                "Ticker": ticker,
                "Menge": asset["Quantity"],
                "Preis": f"€{price:.2f}",
                "Wert": f"€{value:,.2f}",
                "% Anteil": f"{(value / total_portfolio_value * 100):.2f}%"
            })
        else:
            debug_data.append({
                "Ticker": ticker,
                "Menge": asset["Quantity"],
                "Preis": "Fehlend",
                "Wert": "Fehlend",
                "% Anteil": "N/A"
            })
    
    st.dataframe(pd.DataFrame(debug_data))

if __name__ == "__main__":
    main()