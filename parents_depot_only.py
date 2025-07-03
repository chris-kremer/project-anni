import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import pytz
import os
import json

# Initial portfolio and ownership
portfolio_assets = [
    {"Ticker": "URTH", "Quantity": 480, "Name": "Welt Index"},
    {"Ticker": "WFC", "Quantity": 400, "Name": "Wells Fargo (Bank)"},
    {"Ticker": "HLBZF", "Quantity": 185, "Name": "Heidelberg Materials"},
    {"Ticker": "C", "Quantity": 340, "Name": "Citigroup (Bank)"},
    {"Ticker": "BPAQF", "Quantity": 2000, "Name": "British Petroleum (Öl/Gas)"},
    {"Ticker": "POAHF", "Quantity": 150, "Name": "Porsche (Auto)"},
    {"Ticker": "EXV1.DE", "Quantity": 284, "Name": "Bank Index"},
    {"Ticker": "1COV.DE", "Quantity": 100, "Name": "Covestro (Chemie)"},
    {"Ticker": "SPY", "Quantity": 10, "Name": "USA Index"},
    {"Ticker": "HYMTF", "Quantity": 100, "Name": "Hyundai (Auto)"},
    {"Ticker": "SHEL", "Quantity": 75, "Name": "Shell (Öl/Gas)"},
    {"Ticker": "DAX", "Quantity": 0, "Name": "Deutschaland Index"}, # Note: DAX is ^GDAXI on yfinance
    {"Ticker": "PLTR", "Quantity": 100, "Name": "Palantir (Rüstung Software)"},
    {"Ticker": "UQ2B.DU", "Quantity": 5, "Name": "Europa Index"},
    {"Ticker": "DB", "Quantity": 1, "Name": "Deutsche Bank"}, # Note: Might be DBK.DE for Xetra
    {"Ticker": "GS", "Quantity": 9, "Name": "Goldman Sachs (Bank)"},
    {"Ticker": "MBG.DE", "Quantity": 50, "Name": "Mercedes (Auto)"},
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
            return {"Percentage": 62.821735319}
    else:
        return {"Percentage": 67.821735319}

def fetch_historical_prices(tickers):
    historical_prices = {}
    for ticker in tickers:
        # yfinance uses ^GDAXI for DAX index
        actual_ticker = "^GDAXI" if ticker == "DAX" else ticker
        try:
            stock = yf.Ticker(actual_ticker)
            data = stock.history(period="2y", interval="1mo")
            if not data.empty:
                historical_prices[ticker] = data["Close"].ffill() # Keep original ticker key
            else:
                st.warning(f"No historical data for {ticker} ({actual_ticker}).")
                historical_prices[ticker] = None
        except Exception as e:
            print(f"Error fetching historical data for {ticker} ({actual_ticker}): {e}")
            historical_prices[ticker] = None
    return historical_prices


def calculate_value(portfolio, price_dict, initial_cash_val, ownership_data):
    total_value = initial_cash_val
    for asset in portfolio:
        ticker = asset["Ticker"]
        quantity = asset["Quantity"]
        price = price_dict.get(ticker)
        if price is not None and pd.notna(price) and price > 0:
            total_value += price * quantity
    return total_value * (ownership_data["Percentage"] / 100)

def calculate_monthly_share_value(portfolio, historical_prices, ownership_data, initial_cash_val):
    all_dates = set()
    for prices in historical_prices.values():
        if prices is not None:
            all_dates.update(prices.index)
    
    if not all_dates: # Handle case where no historical prices were fetched
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
                    # Try to find the last known price if current is NaN (ffill should handle this in fetch)
                    # This path might be redundant if ffill worked perfectly, but good for safety.
                    valid_prices_before_date = prices_for_asset.loc[prices_for_asset.index <= date].ffill()
                    if not valid_prices_before_date.empty:
                        price = valid_prices_before_date.iloc[-1]
                    else:
                        continue # No valid price found up to this date
                
                if pd.notna(price) and price > 0:
                     total_value_on_date += price * quantity

        share_value = total_value_on_date * (ownership_data["Percentage"] / 100)
        if share_value >= 50000: # Threshold condition
            monthly_values.append({"Date": date, "Share Value": share_value})

    return pd.DataFrame(monthly_values)

def fetch_daily_prices(tickers):
    daily_prices = {}
    for ticker in tickers:
        # yfinance uses ^GDAXI for DAX index
        actual_ticker = "^GDAXI" if ticker == "DAX" else ticker
        try:
            # Fetch slightly more data to ensure previous day is available
            data = yf.download(actual_ticker, period="10d", interval="1d", progress=False)
            if not data.empty:
                if data.index.tz is None:
                    data.index = data.index.tz_localize('UTC')
                data.index = data.index.tz_convert(local_tz)
                daily_prices[ticker] = data # Keep original ticker key
            else:
                st.warning(f"No daily data for {ticker} ({actual_ticker}).")
                daily_prices[ticker] = None
        except Exception as e:
            print(f"Error fetching daily data for {ticker} ({actual_ticker}): {e}")
            daily_prices[ticker] = None
    return daily_prices

def get_scalar_price(row_series, column_name):
    """Safely extracts a scalar price from a row Series, handling potential duplicate columns."""
    if column_name in row_series.index:
        value_or_series = row_series[column_name]
        if isinstance(value_or_series, pd.Series):
            if not value_or_series.empty:
                # Multiple values found for the column name, take the first one.
                scalar_price = value_or_series.iloc[0]
            else:
                scalar_price = None
        else:
            # Single value found, it's already a scalar.
            scalar_price = value_or_series
        
        if pd.notna(scalar_price):
            return float(scalar_price)
    return None

# Previous code ...

def main():
    st.set_page_config(layout="wide")
    st.title("📈 Depot Anteil")
    ownership = load_ownership_data()

    tickers = [asset["Ticker"] for asset in portfolio_assets]
    
    @st.cache_data(ttl=1800) 
    def get_historical_prices_cached(tickers_list):
        return fetch_historical_prices(tickers_list)

    @st.cache_data(ttl=300) 
    def get_daily_prices_cached(tickers_list):
        return fetch_daily_prices(tickers_list)

    historical_prices = get_historical_prices_cached(tuple(tickers)) 
    daily_prices = get_daily_prices_cached(tuple(tickers))

    current_datetime_local = datetime.now(local_tz)
    current_date_local = current_datetime_local.date()
    
    yesterday_open_dict = {}
    current_price_dict = {}

    for ticker in tickers:
        data = daily_prices.get(ticker)
        if data is not None and not data.empty:
            last_row_data = data.iloc[-1]
            current_price_dict[ticker] = get_scalar_price(last_row_data, "Close")
            data_sorted = data.sort_index()
            before_today_df = data_sorted[data_sorted.index.date < current_date_local]
            
            if not before_today_df.empty:
                last_trading_day_before_today_row = before_today_df.iloc[-1]
                yesterday_open_dict[ticker] = get_scalar_price(last_trading_day_before_today_row, "Open")
            else:
                if not data.empty and data.iloc[-1].name.date() < current_date_local :
                     yesterday_open_dict[ticker] = get_scalar_price(data.iloc[-1], "Open")
                elif len(data) > 1 and data.iloc[-2].name.date() < current_date_local:
                    yesterday_open_dict[ticker] = get_scalar_price(data.iloc[-2], "Open")
                else:
                    yesterday_open_dict[ticker] = None
        else:
            current_price_dict[ticker] = None
            yesterday_open_dict[ticker] = None

    current_value = calculate_value(portfolio_assets, current_price_dict, initial_cash, ownership)
    
    total_gross_portfolio_value = initial_cash
    for asset in portfolio_assets:
        price = current_price_dict.get(asset["Ticker"])
        if price is not None and pd.notna(price) and price > 0:
            total_gross_portfolio_value += price * asset["Quantity"]

    col1, col2 = st.columns(2)
    with col1:
        delta_vs_130k = 0
        if current_value is not None and current_value > 0 :
            delta_vs_130k = ((current_value / 130000) - 1) * 100 if 130000 != 0 else 0
        st.metric(
            label="Aktueller Wert (Anteil)",
            value=f"€{current_value:,.2f}" if current_value is not None else "N/A",
            delta=f"{delta_vs_130k:.2f}% vs €130k" if current_value is not None else "",
            delta_color="normal"
        )
    
    with col2:
        yesterday_value = None
        # Check if yesterday_open_dict is not empty and all its values are not None
        if yesterday_open_dict and all(p is not None for p in yesterday_open_dict.values()):
             yesterday_value = calculate_value(portfolio_assets, yesterday_open_dict, initial_cash, ownership)
        
        if current_value is not None and yesterday_value is not None and yesterday_value != 0:
            delta_value_abs = current_value - yesterday_value
            delta_percent = (delta_value_abs / yesterday_value) * 100
            st.metric(
                label="Veränderung seit Gestern (Open)",
                value=f"€{delta_value_abs:+,.2f}",
                delta=f"{delta_percent:+.2f}%",
                delta_color="normal" if delta_percent == 0 else ("inverse" if delta_percent < 0 else "normal")
            )
        else:
            st.metric("Veränderung seit Gestern (Open)", "N/A", help="Möglicherweise fehlen gestrige Eröffnungskurse oder aktuelle Werte.")

    st.subheader("Wertentwicklung (Anteil) über die letzten 2 Jahre:")
    monthly_share_value_df = calculate_monthly_share_value(
        portfolio_assets, historical_prices, ownership, initial_cash
    )

    if not monthly_share_value_df.empty:
        # MODIFICATION STARTS HERE
        # Convert 'Date' column to datetime objects, coercing errors to NaT
        monthly_share_value_df["Date"] = pd.to_datetime(monthly_share_value_df["Date"], errors='coerce')

        # Handle NaT values: remove rows where 'Date' became NaT
        rows_before_dropna = len(monthly_share_value_df)
        monthly_share_value_df.dropna(subset=["Date"], inplace=True)
        rows_after_dropna = len(monthly_share_value_df)

        if rows_before_dropna > rows_after_dropna:
            st.warning(f"{rows_before_dropna - rows_after_dropna} Einträge mit nicht-lesbaren Datumsangaben wurden aus den Verlaufsdaten entfernt.")

        if monthly_share_value_df.empty:
            st.error("Keine gültigen Verlaufsdaten nach der Datumskonvertierung vorhanden. Das Diagramm kann nicht angezeigt werden.")
        else:
            # Proceed with timezone localization only if DataFrame is not empty
            # Ensure all dates are timezone-naive before localizing to UTC, then convert
            # This handles cases where some dates might already be localized due to 'coerce' or other reasons
            
            # Convert to timezone-naive first if mixed, then localize and convert
            # This step might be overly cautious if pd.to_datetime with coerce results in naive or consistent tz for Timestamps
            is_localized = False
            try:
                if monthly_share_value_df["Date"].dt.tz is not None:
                    is_localized = True
            except AttributeError: # Happens if column is not datetime after all (e.g. all NaT and dropped)
                 pass


            if is_localized: # If already localized (e.g. to UTC by some chance)
                 monthly_share_value_df["Date"] = monthly_share_value_df["Date"].dt.tz_convert(local_tz)
            else: # If naive (most common case after to_datetime or if original was naive)
                 monthly_share_value_df["Date"] = monthly_share_value_df["Date"].dt.tz_localize('UTC', ambiguous='infer').dt.tz_convert(local_tz)
            
            # MODIFICATION ENDS HERE
            
            current_ts_for_chart = pd.Timestamp.now(tz=local_tz)
            # Ensure DataFrame is not empty before trying to access .iloc[-1]
            if not monthly_share_value_df.empty:
                last_historical_date = monthly_share_value_df["Date"].iloc[-1]
            
                if current_value is not None and (current_ts_for_chart.normalize() > last_historical_date.normalize() or not any(d.date() == current_ts_for_chart.date() for d in monthly_share_value_df["Date"])):
                    new_entry = pd.DataFrame([{
                        "Date": current_ts_for_chart,
                        "Share Value": current_value
                    }])
                    monthly_share_value_df = pd.concat(
                        [monthly_share_value_df, new_entry],
                        ignore_index=True
                    ).sort_values(by="Date").reset_index(drop=True)

            if not monthly_share_value_df.empty:
                st.line_chart(
                    monthly_share_value_df.set_index("Date")["Share Value"],
                    use_container_width=True
                )
            else:
                st.write("Keine darstellbaren Verlaufsdaten vorhanden.") # Message if df becomes empty after processing
    else:
        st.write("Keine historischen Daten über dem Schwellenwert von €50.000 für den Chart verfügbar oder Fehler beim Laden.")
    
    # ... rest of your main function (debug_data, performance highlights, detailed positions table)
    # This part should be unaffected but ensure it handles an empty current_price_dict or yesterday_open_dict gracefully if all data fetching fails.

    debug_data = []
    max_percentage_gain = {"name": None, "value": -float('inf')}
    max_total_gain = {"name": None, "value": -float('inf')}
    
    for asset in portfolio_assets:
        ticker = asset["Ticker"]
        name = asset["Name"]
        quantity = asset["Quantity"]
        
        current_price = current_price_dict.get(ticker)
        yesterday_open_price = yesterday_open_dict.get(ticker)
        
        price_str = "N/A"
        value_str = "N/A"
        percent_anteil_str = "N/A"
        delta_price_str = "N/A"
        delta_percent_str = "N/A"
        total_gain_str = "N/A"

        if current_price is not None and pd.notna(current_price):
            price_str = f"€{current_price:.2f}"
            value = current_price * quantity
            value_str = f"€{value:,.2f}"
            if total_gross_portfolio_value != 0: # Avoid division by zero
                percent_anteil_str = f"{(value / total_gross_portfolio_value * 100):.2f}%"

            if yesterday_open_price is not None and pd.notna(yesterday_open_price) and yesterday_open_price > 0: # Ensure yesterday_open_price is positive
                delta_price_val = current_price - yesterday_open_price
                delta_percent_val = (delta_price_val / yesterday_open_price) * 100
                total_gain_val = delta_price_val * quantity
                
                delta_price_str = f"€{delta_price_val:+.2f}"
                delta_percent_str = f"{delta_percent_val:+.2f}%"
                total_gain_str = f"€{total_gain_val:+,.2f}"

                if delta_percent_val > max_percentage_gain["value"]:
                    max_percentage_gain = {"name": name, "value": delta_percent_val}
                if total_gain_val > max_total_gain["value"]:
                    max_total_gain = {"name": name, "value": total_gain_val}
        else:
            price_str = "Fehlend" 
            value_str = "Fehlend"
            
        debug_data.append({
            "Ticker": ticker,
            "Name": name,
            "Menge": quantity,
            "Preis": price_str,
            "Wert": value_str,
            "% Anteil": percent_anteil_str,
            "Tagesänderung (€)": delta_price_str,
            "Tagesänderung (%)": delta_percent_str,
            "Gesamtgewinn Heute": total_gain_str 
        })

    st.subheader("🏅 Tagesperformance Highlights")
    valid_percentage_gain = max_percentage_gain["name"] is not None and max_percentage_gain["value"] != -float('inf')
    valid_total_gain = max_total_gain["name"] is not None and max_total_gain["value"] != -float('inf')

    if valid_percentage_gain and valid_total_gain:
        st.success(
            f"🏆 **Beste Performance Heute:** {max_percentage_gain['name']} "
            f"({max_percentage_gain['value']:+.2f}%)\n\n"
            f"💰 **Höchster Gewinn Heute:** {max_total_gain['name']} "
            f"(€{max_total_gain['value']:+,.2f})"
        )
    elif valid_percentage_gain:
         st.info(f"🏆 **Beste Performance Heute:** {max_percentage_gain['name']} ({max_percentage_gain['value']:+.2f}%)")
    elif valid_total_gain:
         st.info(f"💰 **Höchster Gewinn Heute:** {max_total_gain['name']} (€{max_total_gain['value']:+,.2f})")
    else:
        st.warning("⚠️ Keine vollständigen Tagesdaten für Performance Highlights verfügbar.")

    st.subheader("Detaillierte Positionen")
    st.dataframe(
        pd.DataFrame(debug_data),
        height=600,
        use_container_width=True,
        column_config={
            "Menge": st.column_config.NumberColumn(format="%d"),
            # Add other column configs if needed
        }
    )

# Make sure all functions are defined before main() if not already.
# For example, the helper 'get_scalar_price' and others used in main.
# Ensure the portfolio_assets, initial_cash, etc. are defined globally or passed appropriately.

if __name__ == "__main__":
    main()