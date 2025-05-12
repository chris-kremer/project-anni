import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import pytz
import os
import json
import io
import contextlib
import warnings
import logging

# silence noisy libraries
warnings.filterwarnings("ignore")
for lib in ("yfinance", "urllib3", "requests"):
    logging.getLogger(lib).setLevel(logging.CRITICAL)

# Initial portfolio and ownership
portfolio_assets = [
    {"Ticker": "URTH", "Quantity": 520.28, "Name": "Welt Index"},
    {"Ticker": "WFC", "Quantity": 400, "Name": "Wells Fargo (Bank)"},
    {"Ticker": "HLBZF", "Quantity": 185, "Name": "Heidelberg Materials"},
    {"Ticker": "C", "Quantity": 340, "Name": "Citigroup (Bank)"},
    {"Ticker": "BPAQF", "Quantity": 2000, "Name": "British Petroleum (Öl/Gas)"},
    {"Ticker": "POAHF", "Quantity": 0, "Name": "Porsche (Auto)"},
    {"Ticker": "EXV1.DE", "Quantity": 284, "Name": "Bank Index"},
    {"Ticker": "1COV.DE", "Quantity": 100, "Name": "Covestro (Chemie)"},
    {"Ticker": "SPY", "Quantity": 14, "Name": "USA Index"},
    {"Ticker": "HYMTF", "Quantity": 100, "Name": "Hyundai (Auto)"},
    {"Ticker": "SHEL", "Quantity": 75, "Name": "Shell (Öl/Gas)"},
    {"Ticker": "DAX", "Quantity": 6, "Name": "Deutschland Index"},
    {"Ticker": "PLTR", "Quantity": 100, "Name": "Palantir (Rüstung Software)"},
    {"Ticker": "UQ2B.DU", "Quantity": 5, "Name": "Europa Index"},
    {"Ticker": "DB", "Quantity": 1, "Name": "Deutsche Bank"},
    {"Ticker": "GS", "Quantity": 9, "Name": "Goldman Sachs (Bank)"},
    {"Ticker": "MBG.DE", "Quantity": 50, "Name": "Mercedes (Auto)"},
    {"Ticker": "UAL", "Quantity": 60, "Name": "United (Airline)"},
    {"Ticker": "LUV", "Quantity": 100, "Name": "Southwest (Airline)"},

]

initial_cash = 22000
data_file_path = "parents_data.json"
local_tz = pytz.timezone("Europe/Berlin")

def load_ownership_data():
    if os.path.exists(data_file_path):
        try:
            with open(data_file_path, "r") as file:
                data = json.load(file)
                return data.get("ownership", {"Percentage": 0.36262512})
        except json.JSONDecodeError:
            st.warning("Data file is corrupt. Using default values.")
            return {"Percentage": 0.31}
    else:
        return {"Percentage": 0.31}

def fetch_historical_prices(tickers):
    historical_prices = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            data = yf.download(
                tickers,
                period="1y",
                interval="1wk",
                progress=False,
                group_by="ticker",
                threads=True
            )
    except Exception:
        return {t: None for t in tickers}

    for ticker in tickers:
        try:
            df = data[ticker] if isinstance(data, dict) or (ticker in data) else data
            close = df["Close"] if "Close" in df else None
            historical_prices[ticker] = close.ffill() if close is not None and not close.empty else None
        except Exception:
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

def calculate_weekly_share_value(portfolio, historical_prices, ownership, initial_cash):
    all_dates = set()
    for prices in historical_prices.values():
        if prices is not None:
            all_dates.update(prices.index)
    all_dates = sorted(all_dates)

    weekly_values = []
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
        if share_value >= 500:  # Keep threshold for valid values
            weekly_values.append({"Date": date, "Share Value": share_value})

    return pd.DataFrame(weekly_values)

def fetch_daily_prices(tickers):
    daily_prices = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            data = yf.download(
                tickers,
                period="7d",
                interval="1d",
                progress=False,
                group_by="ticker",
                threads=True
            )
    except Exception:
        return {t: None for t in tickers}

    for ticker in tickers:
        try:
            df = data[ticker] if isinstance(data, dict) or (ticker in data) else data
            if df.empty:
                daily_prices[ticker] = None
            else:
                df.index = df.index.tz_localize('UTC').tz_convert(local_tz)
                daily_prices[ticker] = df
        except Exception:
            daily_prices[ticker] = None
    return daily_prices

def main():
    st.title("Anni's Aktien")
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
                    yesterday_open_dict[ticker] = before_today.iloc[-1]["Open"].item()
                except (KeyError, AttributeError):
                    yesterday_open_dict[ticker] = None

    # Current price dictionary
    current_price_dict = {}
    for ticker in tickers:
        data = daily_prices.get(ticker)
        if data is not None and not data.empty:
            try:
                current_price_dict[ticker] = data.iloc[-1]["Close"].item()
            except (KeyError, AttributeError):
                current_price_dict[ticker] = None

    # Calculate current value
    current_value = calculate_value(portfolio_assets, current_price_dict, initial_cash, ownership)
    total_portfolio_value = sum(
        price * asset["Quantity"] for asset, price in zip(portfolio_assets, current_price_dict.values())
    ) + initial_cash

    # Display metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Aktueller Wert",
            value=f"€{current_value:,.2f}",
            delta=f"{((current_value / 800) - 1) * 100:.2f}%",
            delta_color="normal"
        )
    
    with col2:
        if yesterday_open_dict:
            yesterday_value = calculate_value(portfolio_assets, yesterday_open_dict, initial_cash, ownership)
            delta_value = current_value - yesterday_value
            delta_percent = (delta_value / yesterday_value) * 100 if yesterday_value != 0 else 0
            st.metric(
                label="Seit gestern morgen",
                value=f"€{delta_value:+,.2f}",
                delta=f"{delta_percent:+.2f}%",
                delta_color="normal"
            )
        else:
            st.metric("Seit gestern Open", "N/A")
    
    # Chart: 1 Jahr Performance des Portfolios (Standardisiert)
    st.subheader("1 Jahr Performance des Portfolios (Standardisiert)")
    weekly_share_value = calculate_weekly_share_value(
        portfolio_assets, historical_prices, ownership, initial_cash
    )

    if not weekly_share_value.empty:
        # Ensure timestamps are timezone‑aware (assumed UTC) before conversion
        weekly_share_value["Date"] = (
            pd.to_datetime(weekly_share_value["Date"], utc=True)
              .dt.tz_convert(local_tz)
        )
        current_ts = pd.Timestamp.now(tz=local_tz)
        last_date = weekly_share_value["Date"].iloc[-1]
        
        if current_ts > last_date:
            new_entry = pd.DataFrame([{
                "Date": current_ts,
                "Share Value": current_value
            }])
            weekly_share_value = pd.concat(
                [weekly_share_value, new_entry],
                ignore_index=True
            )
        
        # Standardize the portfolio values: set the first value to 100 and scale the rest accordingly
        baseline = weekly_share_value["Share Value"].iloc[0]
        weekly_share_value["Standardized"] = (weekly_share_value["Share Value"] / baseline) * 100

        st.line_chart(
            weekly_share_value.set_index("Date")["Standardized"],
            use_container_width=True
        )
    else:
        st.write("Keine Daten über dem Schwellenwert von €50.000 verfügbar.")

    # Calculate performance data and prepare table
    debug_data = []
    max_percentage_gain = {"name": None, "value": -float('inf')}
    max_total_gain = {"name": None, "value": -float('inf')}
    
    for asset in portfolio_assets:
        ticker = asset["Ticker"]
        name = asset["Name"]
        data = daily_prices.get(ticker)
        quantity = asset["Quantity"]
        
        if data is not None and not data.empty:
            try:
                price = data.iloc[-1]["Close"].item()
                value = price * quantity
                yesterday_open = yesterday_open_dict.get(ticker)
                
                if yesterday_open and yesterday_open > 0 and price:
                    delta_price = price - yesterday_open
                    delta_percent = (delta_price / yesterday_open) * 100
                    total_gain = delta_price * quantity * ownership["Percentage"] * 0.01
                    
                    # Update performance trackers
                    if delta_percent > max_percentage_gain["value"]:
                        max_percentage_gain = {"name": name, "value": delta_percent}
                    if total_gain > max_total_gain["value"]:
                        max_total_gain = {"name": name, "value": total_gain}
                        
                    delta_price_str = f"€{delta_price:+.2f}"
                    delta_percent_str = f"{delta_percent:+.2f}%"
                    total_gain_str = f"€{total_gain:+,.2f}"
                else:
                    delta_price_str = "N/A"
                    delta_percent_str = "N/A"
                    total_gain_str = "N/A"

                debug_data.append({
                    "Name": name,
                    "Menge": quantity,
                    "Preis": f"€{price:.2f}",
                    "Wert": f"€{value:,.2f}",
                    "% Anteil": f"{(value / total_portfolio_value * 100):.2f}%",
                    "Tagesänderung (%)": delta_percent_str,
                    "Gewinn für dich": total_gain_str
                })
                
            except (KeyError, AttributeError):
                debug_data.append({
                    "Ticker": ticker,
                    "Name": name,
                    "Menge": quantity,
                    "Preis": "Fehler",
                    "Wert": "Fehler",
                    "% Anteil": "N/A",
                    "Tagesänderung (€)": "N/A",
                    "Tagesänderung (%)": "N/A",
                    "Gesamtgewinn": "N/A"
                })
        else:
            debug_data.append({
                "Ticker": ticker,
                "Name": name,
                "Menge": quantity,
                "Preis": "Fehlend",
                "Wert": "Fehlend",
                "% Anteil": "N/A",
                "Tagesänderung (€)": "N/A",
                "Tagesänderung (%)": "N/A",
                "Gesamtgewinn": "N/A"
            })

    # Performance highlights above the table
    st.subheader("Tagesperformance")
    if max_percentage_gain["name"] and max_total_gain["name"]:
        adjusted_best_total_gain = max_total_gain["value"] 
        st.success(
            f"🏆 **Beste Performance Heute:** {max_percentage_gain['name']} "
            f"({max_percentage_gain['value']:.2f}%)\n\n"
            f"💰 **Höchster Gewinn Heute:** {max_total_gain['name']} "
            f"(€{adjusted_best_total_gain:+,.2f} für dich)"
        )
    elif max_percentage_gain["name"] or max_total_gain["name"]:
        st.warning("⚠️ Teilweise Daten verfügbar:")
        if max_percentage_gain["name"]:
            st.write(f"- 🥇 {max_percentage_gain['name']} ({max_percentage_gain['value']:.2f}%)")
        if max_total_gain["name"]:
            adjusted_best_total_gain = max_total_gain["value"] * ownership["Percentage"]
            st.write(f"- 🥇 {max_total_gain['name']} (€{adjusted_best_total_gain:+,.2f})")
    else:
        st.warning("⚠️ Keine vollständigen Tagesdaten verfügbar")

    # Detailed positions table
    st.subheader("Detaillierte Positionen")
    st.dataframe(
        pd.DataFrame(debug_data),
        height=600,
        use_container_width=True
    )

if __name__ == "__main__":
    main()