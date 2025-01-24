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
    
    # Yesterday's open values
    yesterday_open_dict = {}
    for ticker in tickers:
        data = daily_prices.get(ticker)
        if data is not None and not data.empty:
            before_today = data[data.index.date < current_date]
            if not before_today.empty:
                try:
                    # Explicitly convert to scalar
                    yesterday_open_dict[ticker] = before_today.iloc[-1]["Open"].item()
                except (KeyError, AttributeError):
                    yesterday_open_dict[ticker] = None

    # Current price dictionary
    current_price_dict = {}
    for ticker in tickers:
        data = daily_prices.get(ticker)
        if data is not None and not data.empty:
            try:
                # Ensure scalar conversion
                current_price_dict[ticker] = data.iloc[-1]["Close"].item()
            except (KeyError, AttributeError):
                current_price_dict[ticker] = None

    # Calculate current value
    current_value = calculate_value(portfolio_assets, current_price_dict, initial_cash, ownership)
    total_portfolio_value = sum(
        price * asset["Quantity"] for asset, price in zip(portfolio_assets, current_price_dict.values())
    ) + initial_cash

    # Display metrics (unchanged)
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Aktueller Wert",
            value=f"€{current_value:,.2f}",
            delta=f"{((current_value / 130000) - 1) * 100:.2f}%",
            delta_color="normal"
        )
    
    with col2:
        if yesterday_open_dict:
            yesterday_value = calculate_value(portfolio_assets, yesterday_open_dict, initial_cash, ownership)
            delta_value = current_value - yesterday_value
            delta_percent = (delta_value / yesterday_value) * 100 if yesterday_value != 0 else 0
            st.metric(
                label="Seit gestern",
                value=f"€{delta_value:+,.2f}",
                delta=f"{delta_percent:+.2f}%",
                delta_color="normal"
            )
        else:
            st.metric("Seit gestern Open", "N/A")

    # Chart section (unchanged)
    st.subheader("Wertentwicklung über die letzten 2 Jahre")
    monthly_share_value = calculate_monthly_share_value(
        portfolio_assets, historical_prices, ownership, initial_cash
    )

    if not monthly_share_value.empty:
        monthly_share_value["Date"] = monthly_share_value["Date"].dt.tz_convert(local_tz)
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

    # Detailed positions table (unchanged)
    st.subheader("Detaillierte Aktienpositionen")
    debug_data = []
    for asset in portfolio_assets:
        ticker = asset["Ticker"]
        data = daily_prices.get(ticker)
        if data is not None and not data.empty:
            try:
                price = data.iloc[-1]["Close"].item()  # Scalar conversion
                value = price * asset["Quantity"]
                yesterday_open = yesterday_open_dict.get(ticker)
                
                # Calculate daily changes
                if yesterday_open and yesterday_open > 0:
                    delta_price = price - yesterday_open
                    delta_percent = (delta_price / yesterday_open) * 100
                    delta_price_str = f"€{delta_price:+.2f}"
                    delta_percent_str = f"{delta_percent:+.2f}%"
                else:
                    delta_price_str = "N/A"
                    delta_percent_str = "N/A"

                debug_data.append({
                    "Ticker": ticker,
                    "Menge": asset["Quantity"],
                    "Preis": f"€{price:.2f}",
                    "Wert": f"€{value:,.2f}",
                    "% Anteil": f"{(value / total_portfolio_value * 100):.2f}%",
                    "Tagesänderung (€)": delta_price_str,
                    "Tagesänderung (%)": delta_percent_str
                })
            except (KeyError, AttributeError):
                debug_data.append({
                    "Ticker": ticker,
                    "Menge": asset["Quantity"],
                    "Preis": "Fehler",
                    "Wert": "Fehler",
                    "% Anteil": "N/A",
                    "Tagesänderung (€)": "N/A",
                    "Tagesänderung (%)": "N/A"
                })
        else:
            debug_data.append({
                "Ticker": ticker,
                "Menge": asset["Quantity"],
                "Preis": "Fehlend",
                "Wert": "Fehlend",
                "% Anteil": "N/A",
                "Tagesänderung (€)": "N/A",
                "Tagesänderung (%)": "N/A"
            })

    st.dataframe(pd.DataFrame(debug_data))

if __name__ == "__main__":
    main()