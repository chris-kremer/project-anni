import yfinance as yf
import pandas as pd
import streamlit as st
import pytz

# Default timezone used for date conversions
DEFAULT_TZ = pytz.timezone("Europe/Berlin")


def fetch_historical_prices(tickers, period="2y", interval="1mo"):
    """Fetch monthly historical prices for a list of tickers."""
    historical_prices = {}
    for ticker in tickers:
        actual_ticker = "^GDAXI" if ticker == "DAX" else ticker
        try:
            stock = yf.Ticker(actual_ticker)
            data = stock.history(period=period, interval=interval)
            if not data.empty:
                historical_prices[ticker] = data["Close"].ffill()
            else:
                st.warning(f"No historical data for {ticker} ({actual_ticker}).")
                historical_prices[ticker] = None
        except Exception as e:
            print(f"Error fetching historical data for {ticker} ({actual_ticker}): {e}")
            historical_prices[ticker] = None
    return historical_prices


def fetch_daily_prices(tickers, local_tz=DEFAULT_TZ):
    """Fetch recent daily prices for a list of tickers."""
    daily_prices = {}
    for ticker in tickers:
        actual_ticker = "^GDAXI" if ticker == "DAX" else ticker
        try:
            data = yf.download(actual_ticker, period="10d", interval="1d", progress=False)
            if not data.empty:
                if data.index.tz is None:
                    data.index = data.index.tz_localize('UTC')
                daily_prices[ticker] = data.tz_convert(local_tz)
            else:
                st.warning(f"No daily data for {ticker} ({actual_ticker}).")
                daily_prices[ticker] = None
        except Exception as e:
            print(f"Error fetching daily data for {ticker} ({actual_ticker}): {e}")
            daily_prices[ticker] = None
    return daily_prices


def calculate_value(portfolio, price_dict, initial_cash_val, ownership_data):
    """Calculate current portfolio value based on provided prices."""
    total_value = initial_cash_val
    for asset in portfolio:
        ticker = asset["Ticker"]
        quantity = asset["Quantity"]
        price = price_dict.get(ticker)
        if price is not None and pd.notna(price) and price > 0:
            total_value += price * quantity
    return total_value * (ownership_data["Percentage"] / 100)


def calculate_monthly_share_value(portfolio, historical_prices, ownership_data, initial_cash_val, threshold=0):
    """Create a DataFrame with monthly share values filtered by a threshold."""
    all_dates = set()
    for prices in historical_prices.values():
        if prices is not None:
            all_dates.update(prices.index)

    if not all_dates:
        return pd.DataFrame(columns=["Date", "Share Value"])

    all_dates = sorted(list(all_dates))
    monthly_values = []

    for date in all_dates:
        total_value_on_date = initial_cash_val
        for asset in portfolio:
            ticker = asset["Ticker"]
            quantity = asset["Quantity"]
            prices_for_asset = historical_prices.get(ticker)
            if prices_for_asset is not None and date in prices_for_asset.index:
                price = prices_for_asset.loc[date]
                if pd.isna(price) or price <= 0:
                    valid = prices_for_asset.loc[prices_for_asset.index <= date].ffill()
                    if not valid.empty:
                        price = valid.iloc[-1]
                    else:
                        continue
                if pd.notna(price) and price > 0:
                    total_value_on_date += price * quantity
        share_value = total_value_on_date * (ownership_data["Percentage"] / 100)
        if share_value >= threshold:
            monthly_values.append({"Date": date, "Share Value": share_value})

    return pd.DataFrame(monthly_values)


def get_scalar_price(row_series, column_name):
    """Safely extract a scalar price from a pandas Series."""
    if column_name in row_series.index:
        value_or_series = row_series[column_name]
        if isinstance(value_or_series, pd.Series):
            if not value_or_series.empty:
                scalar_price = value_or_series.iloc[0]
            else:
                scalar_price = None
        else:
            scalar_price = value_or_series
        if pd.notna(scalar_price):
            return float(scalar_price)
    return None

