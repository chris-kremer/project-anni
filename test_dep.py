import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta
import pytz
import os
import json
from typing import List, Dict, Any, Tuple, Optional

# --- Configuration ---

# Portfolio Definition
PORTFOLIO_ASSETS: List[Dict[str, Any]] = [
    {"Ticker": "URTH", "Quantity": 480, "Name": "Welt Index"},
    {"Ticker": "WFC", "Quantity": 400, "Name": "Wells Fargo (Bank)"},
    {"Ticker": "HLBZF", "Quantity": 185, "Name": "Heidelberg Materials"}, # Consider HEI.DE if available
    {"Ticker": "C", "Quantity": 340, "Name": "Citigroup (Bank)"},
    {"Ticker": "BP", "Quantity": 2000, "Name": "BP (Öl/Gas)"}, # Changed BPAQF to BP (more common)
    {"Ticker": "POAHY", "Quantity": 150, "Name": "Porsche (Auto)"}, # Changed POAHF to POAHY (ADR)
    {"Ticker": "EXV1.DE", "Quantity": 284, "Name": "Bank Index"},
    {"Ticker": "1COV.DE", "Quantity": 100, "Name": "Covestro (Chemie)"},
    {"Ticker": "SPY", "Quantity": 10, "Name": "USA Index"},
    {"Ticker": "HYMTF", "Quantity": 100, "Name": "Hyundai (Auto)"}, # Consider 005380.KS if needed
    {"Ticker": "SHEL", "Quantity": 75, "Name": "Shell (Öl/Gas)"},
    {"Ticker": "^GDAXI", "Quantity": 6, "Name": "Deutschland Index"}, # Changed DAX to ^GDAXI
    {"Ticker": "PLTR", "Quantity": 100, "Name": "Palantir (Software)"}, # Simplified name
    {"Ticker": "EXSA.DE", "Quantity": 5, "Name": "Europa Index"}, # Changed UQ2B.DU / STOXX50E to iShares STOXX Europe 600 UCITS ETF (DE) as example
    {"Ticker": "DBK.DE", "Quantity": 1, "Name": "Deutsche Bank"}, # Changed DB to DBK.DE
    {"Ticker": "GS", "Quantity": 9, "Name": "Goldman Sachs (Bank)"},
    {"Ticker": "MBG.DE", "Quantity": 50, "Name": "Mercedes-Benz Group"}, # Updated name
]

INITIAL_CASH: float = 17000.0
OWNERSHIP_DATA_FILE: str = "parents_data.json" # File to store ownership percentage
LOCAL_TZ_NAME: str = "Europe/Berlin" # Timezone for display
LOCAL_TZ = pytz.timezone(LOCAL_TZ_NAME)

# --- Constants ---
DEFAULT_OWNERSHIP_PERCENTAGE: float = 29.4365599 # Default if file is missing/corrupt
HISTORICAL_PERIOD: str = "1y" # Fetch 1 year of data
HISTORICAL_INTERVAL: str = "1wk" # Use weekly intervals for the chart
DAILY_PERIOD: str = "5d" # Fetch last 5 days for current/previous day prices
DAILY_INTERVAL: str = "1d" # Use daily intervals
BASELINE_VALUE_FOR_DELTA: float = 650.0 # Baseline for the first metric's delta calculation (set to 0 or None to disable)
HISTORICAL_VALUE_THRESHOLD: float = 500.0 # Minimum portfolio share value to include in historical chart

# --- Data Loading ---

def load_ownership_data(file_path: str) -> float:
    """Loads ownership percentage from a JSON file."""
    default_value = DEFAULT_OWNERSHIP_PERCENTAGE
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as file:
                data = json.load(file)
                # Allow for different keys, but prefer "Percentage"
                percentage = data.get("Percentage", data.get("ownership", default_value))
                if isinstance(percentage, (int, float)):
                    # Ensure percentage is within a reasonable range
                    if 0 <= float(percentage) <= 100:
                         return float(percentage)
                    else:
                         st.warning(f"Ownership percentage ({percentage}) in {file_path} is outside the 0-100 range. Using default.")
                         return default_value
                else:
                    st.warning(f"Invalid 'Percentage' format in {file_path}. Using default.")
                    return default_value
        except json.JSONDecodeError:
            st.warning(f"{file_path} is corrupt. Using default ownership percentage.")
            return default_value
        except Exception as e:
            st.error(f"Error loading ownership data from {file_path}: {e}")
            return default_value
    else:
        # Only show info message if file is expected but not found
        # st.info(f"{file_path} not found. Using default ownership percentage.")
        return default_value

# --- Data Fetching (with enhanced error visibility) ---

@st.cache_data(ttl=900) # Cache data for 15 minutes
def fetch_historical_prices(tickers: List[str]) -> Dict[str, Optional[pd.Series]]:
    """Fetches 1-year weekly historical closing prices for given tickers."""
    historical_prices: Dict[str, Optional[pd.Series]] = {}
    st.write(f"Fetching historical data ({HISTORICAL_PERIOD}, {HISTORICAL_INTERVAL}) for {len(tickers)} tickers...") # Show progress
    try:
        ticker_objs = yf.Tickers(tickers)
        # Use pandas Panel/MultiIndex DataFrame if available, otherwise fallback
        # Note: yfinance behavior might vary; direct history call often preferred now
        hist_data = ticker_objs.history(period=HISTORICAL_PERIOD, interval=HISTORICAL_INTERVAL)

        if not hist_data.empty and 'Close' in hist_data.columns:
            close_prices = hist_data['Close']
            for ticker in tickers:
                if ticker in close_prices.columns and not close_prices[ticker].isnull().all():
                     # Forward fill missing values within the series for a ticker
                    historical_prices[ticker] = close_prices[ticker].ffill()
                else:
                     historical_prices[ticker] = None # Ticker might lack data or be invalid
        else: # Handle case where no data is returned at all
             for ticker in tickers:
                  historical_prices[ticker] = None

    except Exception as e:
        st.error(f"Error fetching historical data batch: {e}. Trying individual fetches...")
        # Fallback to individual fetching if batch fails
        for ticker in tickers:
             if ticker not in historical_prices: # Only fetch if not already attempted/failed
                 try:
                     stock = yf.Ticker(ticker)
                     data = stock.history(period=HISTORICAL_PERIOD, interval=HISTORICAL_INTERVAL)
                     if not data.empty and 'Close' in data.columns and not data['Close'].isnull().all():
                         historical_prices[ticker] = data["Close"].ffill()
                     else:
                         historical_prices[ticker] = None
                 except Exception as e_single:
                     # Don't flood with warnings, will be summarized later
                     historical_prices[ticker] = None # Ensure it's marked as failed

    # Debugging: Check fetched data locally (uncomment to use)
    # print("--- Historical Prices Fetched ---")
    # for ticker, data in historical_prices.items():
    #     status = "OK" if data is not None and not data.empty else "Failed/Empty"
    #     print(f"{ticker}: Status = {status}, Type = {type(data)}")
    # print("--------------------------------------")

    failed_tickers = [ticker for ticker, data in historical_prices.items() if data is None]
    if failed_tickers:
        st.warning(f"Could not fetch historical data for: {', '.join(failed_tickers)}")

    return historical_prices

@st.cache_data(ttl=300) # Cache data for 5 minutes
def fetch_daily_prices(tickers: List[str]) -> Dict[str, Optional[pd.DataFrame]]:
    """Fetches recent daily OHLC prices for given tickers."""
    daily_prices: Dict[str, Optional[pd.DataFrame]] = {}
    st.write(f"Fetching recent daily data ({DAILY_PERIOD}, {DAILY_INTERVAL}) for {len(tickers)} tickers...") # Show progress
    try:
        data = yf.download(
            tickers=tickers,
            period=DAILY_PERIOD,
            interval=DAILY_INTERVAL,
            progress=False,
            group_by='ticker' # Keep data separated by ticker
        )

        if data.empty or data.shape[0] == 0 :
             st.warning("yf.download returned no recent daily data.")
             for ticker in tickers:
                 daily_prices[ticker] = None
             return daily_prices

        for ticker in tickers:
            try:
                 # Access ticker data, handle multi-index columns if necessary
                 ticker_data = data[ticker] if len(tickers) > 1 else data
                 ticker_data = ticker_data.dropna(how='all') # Drop rows where all columns are NaN

                 if not ticker_data.empty:
                     # Ensure index is DatetimeIndex and localize/convert timezone
                     if not isinstance(ticker_data.index, pd.DatetimeIndex):
                         ticker_data.index = pd.to_datetime(ticker_data.index)

                     if ticker_data.index.tz is None:
                         ticker_data.index = ticker_data.index.tz_localize('UTC')
                     daily_prices[ticker] = ticker_data.tz_convert(LOCAL_TZ)
                 else:
                     daily_prices[ticker] = None
            except KeyError:
                 # This ticker was likely invalid or had no data in the download
                 daily_prices[ticker] = None
            except Exception as e_inner:
                 st.warning(f"Error processing daily data for {ticker}: {e_inner}")
                 daily_prices[ticker] = None

    except Exception as e:
        st.error(f"General error during yf.download for daily prices: {e}")
        # Mark all as potentially failed if the download itself errored
        for ticker in tickers:
            if ticker not in daily_prices: # Avoid overwriting successful processing before error
                 daily_prices[ticker] = None

    failed_tickers = [ticker for ticker, df in daily_prices.items() if df is None]
    if failed_tickers:
        st.warning(f"Could not fetch recent daily data for: {', '.join(failed_tickers)}")

    return daily_prices

# --- Calculation Functions ---

def get_relevant_prices(
    daily_data: Dict[str, Optional[pd.DataFrame]],
    tickers: List[str]
) -> Tuple[Dict[str, Optional[float]], Dict[str, Optional[float]]]:
    """
    Extracts the latest closing price and the previous day's opening price.
    Handles potential missing data gracefully.
    """
    current_prices: Dict[str, Optional[float]] = {}
    yesterday_open_prices: Dict[str, Optional[float]] = {}
    current_date_local: date = datetime.now(LOCAL_TZ).date()

    for ticker in tickers:
        data = daily_data.get(ticker)
        current_prices[ticker] = None
        yesterday_open_prices[ticker] = None

        if data is not None and not data.empty and isinstance(data.index, pd.DatetimeIndex):
            data = data.sort_index() # Ensure data is sorted by date

            # Get the latest available closing price
            try:
                # Use .last('1D') or similar if needed, but iloc[-1] usually works for recent data
                latest_close = data["Close"].dropna().iloc[-1]
                current_prices[ticker] = float(latest_close)
            except (IndexError, KeyError, TypeError):
                # Warning not usually needed unless debugging specific ticker
                pass # Leave as None

            # Get the opening price of the last trading day *before* today
            try:
                # Filter for days strictly before the current local date
                previous_days_data = data[data.index.date < current_date_local]
                if not previous_days_data.empty:
                    # Get the 'Open' price of the most recent day in the filtered data
                    yesterday_open = previous_days_data["Open"].dropna().iloc[-1]
                    yesterday_open_prices[ticker] = float(yesterday_open)
            except (IndexError, KeyError, TypeError):
                 # Warning not usually needed unless debugging specific ticker
                 pass # Leave as None

    return current_prices, yesterday_open_prices

def calculate_portfolio_value(
    portfolio: List[Dict[str, Any]],
    price_dict: Dict[str, Optional[float]],
    cash: float,
    ownership_percentage: float
) -> float:
    """Calculates the value of the owned share of the portfolio based on given prices."""
    total_value = cash
    for asset in portfolio:
        ticker = asset["Ticker"]
        quantity = asset.get("Quantity", 0)
        price = price_dict.get(ticker) # Returns None if ticker not in dict

        # Ensure price is a valid positive number
        if price is not None and pd.notna(price) and price > 0 and quantity > 0:
            total_value += price * quantity

    # Ensure ownership is valid before calculation
    owner_share = 0.0
    if 0 <= ownership_percentage <= 100:
         owner_share = total_value * (ownership_percentage / 100.0)
    else:
         st.error(f"Invalid ownership percentage ({ownership_percentage}) used in calculation.")

    return owner_share

def calculate_historical_share_value(
    portfolio: List[Dict[str, Any]],
    historical_prices: Dict[str, Optional[pd.Series]],
    ownership_percentage: float,
    cash: float
) -> pd.DataFrame:
    """
    Calculates the historical weekly value of the owned share.
    Returns a DataFrame with 'Date' and 'Share Value' columns, even if empty.
    """
    output_columns = ["Date", "Share Value"]
    valid_historical_prices = {
        t: p for t, p in historical_prices.items()
        if p is not None and not p.empty and isinstance(p.index, pd.DatetimeIndex)
    }

    if not valid_historical_prices:
        # st.info("No valid historical price data available for chart calculation.")
        return pd.DataFrame(columns=output_columns)

    # Combine all valid dates from historical price series
    all_dates = set()
    for prices in valid_historical_prices.values():
        all_dates.update(prices.index)

    if not all_dates:
         # st.info("No dates found in the historical price data.")
         return pd.DataFrame(columns=output_columns)

    sorted_dates = sorted(list(all_dates))
    historical_values_data = []

    for date_ts in sorted_dates:
        # Calculate total portfolio value for this specific date
        daily_total_value = cash
        for asset in portfolio:
            ticker = asset["Ticker"]
            quantity = asset.get("Quantity", 0)
            prices = valid_historical_prices.get(ticker) # Get the Series for the ticker

            # Check if this ticker has data and if the current date exists in its index
            if prices is not None and date_ts in prices.index:
                price = prices.loc[date_ts]
                # Use the price only if it's a valid positive number
                if pd.notna(price) and price > 0 and quantity > 0:
                    daily_total_value += price * quantity
            # If price is missing for a specific date (after ffill), we effectively use the last known value
            # implicitly if quantity > 0, or just skip if quantity is 0.

        # Calculate the owner's share for that date
        share_value = 0.0
        if 0 <= ownership_percentage <= 100:
             share_value = daily_total_value * (ownership_percentage / 100.0)

        # Only include data points above the threshold
        if share_value >= HISTORICAL_VALUE_THRESHOLD:
            historical_values_data.append({"Date": date_ts, "Share Value": share_value})

    # Create DataFrame from the collected data
    if not historical_values_data:
        # st.info(f"No historical data points met the threshold of €{HISTORICAL_VALUE_THRESHOLD:,.2f}.")
        return pd.DataFrame(columns=output_columns)
    else:
        result_df = pd.DataFrame(historical_values_data)
        # Ensure 'Date' column is datetime type
        result_df['Date'] = pd.to_datetime(result_df['Date'])
        return result_df


# --- Table and Performance Analysis ---

def generate_positions_dataframe(
    portfolio: List[Dict[str, Any]],
    current_prices: Dict[str, Optional[float]],
    yesterday_open_prices: Dict[str, Optional[float]],
    cash: float, # Pass cash to calculate total value accurately
    ownership_percentage: float
) -> pd.DataFrame:
    """Creates a DataFrame detailing each position's current status and daily change."""
    table_data = []
    total_portfolio_asset_value = 0.0

    # --- First pass: Calculate total *asset* value for percentage calculation ---
    valid_current_prices = {t: p for t, p in current_prices.items() if p is not None and p > 0}
    for asset in portfolio:
        ticker = asset["Ticker"]
        quantity = asset.get("Quantity", 0)
        price = valid_current_prices.get(ticker)
        if price and quantity > 0:
            total_portfolio_asset_value += price * quantity

    total_portfolio_value_incl_cash = total_portfolio_asset_value + cash
    # Avoid division by zero if total value is somehow zero
    denominator_for_pct = total_portfolio_value_incl_cash if total_portfolio_value_incl_cash != 0 else 1.0

    # --- Second pass: Build the table rows ---
    for asset in portfolio:
        ticker = asset["Ticker"]
        name = asset.get("Name", ticker) # Default to ticker if name is missing
        quantity = asset.get("Quantity", 0)

        price = current_prices.get(ticker)
        yesterday_open = yesterday_open_prices.get(ticker)

        # --- Formatting ---
        price_str = f"€{price:,.2f}" if price is not None else "N/A"
        value = price * quantity if price is not None and quantity > 0 else 0.0
        value_str = f"€{value:,.2f}" if price is not None else "N/A"
        # Calculate percentage share of total portfolio (incl. cash)
        share_pct_str = f"{(value / denominator_for_pct * 100):.2f}%" if value > 0 else "0.00%"

        # --- Daily Change Calculation ---
        delta_percent_str = "N/A"
        owner_gain_str = "N/A"
        # Store numeric values for sorting/analysis
        delta_percent_num = 0.0
        owner_gain_num = 0.0

        # Calculate change only if current price and yesterday's open are valid positive numbers
        if price is not None and price > 0 and yesterday_open is not None and yesterday_open > 0 and quantity > 0:
            delta_price = price - yesterday_open
            delta_percent_num = (delta_price / yesterday_open) * 100
            # Calculate the gain/loss attributable to the owner's share for this asset today
            owner_gain_num = delta_price * quantity * (ownership_percentage / 100.0)

            delta_percent_str = f"{delta_percent_num:+.2f}%"
            owner_gain_str = f"€{owner_gain_num:+,.2f}"
        elif price is not None and yesterday_open is None:
             # Handle case where we have current price but no previous open
             delta_percent_str = "Vortag fehlt"
             owner_gain_str = "Vortag fehlt"


        table_data.append({
            "Name": name,
            "Menge": quantity,
            "Preis": price_str,
            "Wert": value_str,
            "% Anteil": share_pct_str,
            "Tagesänderung (%)": delta_percent_str, # Primary change metric
            "Gewinn für dich": owner_gain_str,     # Owner's gain/loss for the day
            # Internal numeric columns for sorting
            "_numeric_delta_percent": delta_percent_num,
            "_numeric_owner_gain": owner_gain_num,
            "_ticker": ticker # Keep ticker for potential future use
        })

    return pd.DataFrame(table_data)


def find_top_performers(positions_df: pd.DataFrame) -> Tuple[Optional[Dict], Optional[Dict]]:
    """Identifies the assets with the highest % gain and highest absolute gain for the owner."""
    # Ensure DataFrame is not empty and has the required numeric columns
    if positions_df.empty or "_numeric_delta_percent" not in positions_df.columns or "_numeric_owner_gain" not in positions_df.columns:
        return None, None

    # Filter out rows where performance couldn't be calculated (value is still 0.0)
    valid_perf_df = positions_df[positions_df["_numeric_delta_percent"] != 0.0].copy()
    valid_gain_df = positions_df[positions_df["_numeric_owner_gain"] != 0.0].copy()


    top_pct = None
    if not valid_perf_df.empty:
        # Find the row with the maximum percentage change
         best_pct_row = valid_perf_df.loc[valid_perf_df["_numeric_delta_percent"].idxmax()]
         top_pct = {"name": best_pct_row["Name"], "value": best_pct_row["_numeric_delta_percent"]}

    top_gain = None
    if not valid_gain_df.empty:
         # Find the row with the maximum owner gain
         best_gain_row = valid_gain_df.loc[valid_gain_df["_numeric_owner_gain"].idxmax()]
         top_gain = {"name": best_gain_row["Name"], "value": best_gain_row["_numeric_owner_gain"]}

    return top_pct, top_gain


# --- Streamlit App Main Function ---

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(page_title="Anni's Aktien", layout="wide")
    st.title("📈 Anni's Aktien Portfolio")

    # --- 1. Load Configuration ---
    ownership_percentage = load_ownership_data(OWNERSHIP_DATA_FILE)
    st.sidebar.metric("Dein Anteil am Portfolio", f"{ownership_percentage:.2f}%")
    st.sidebar.info(f"Anfängliches Bargeld: €{INITIAL_CASH:,.2f}")

    # Extract tickers from portfolio definition
    tickers = [asset["Ticker"] for asset in PORTFOLIO_ASSETS]
    if not tickers:
        st.error("Portfolio ist leer. Bitte Konfiguration prüfen.")
        return # Stop execution if no assets defined

    # --- 2. Fetch Data (using cached functions) ---
    # Use placeholders for spinners while data is fetched/calculated
    fetch_status = st.empty()
    fetch_status.info("Lade Finanzdaten...")
    historical_prices = fetch_historical_prices(tickers)
    daily_prices = fetch_daily_prices(tickers)
    fetch_status.empty() # Clear the status message

    # --- 3. Process Prices ---
    current_prices, yesterday_open_prices = get_relevant_prices(daily_prices, tickers)

    # --- 4. Calculate Portfolio Values ---
    # Check if we have any current prices to calculate value
    if not any(p is not None for p in current_prices.values()):
         st.error("Konnte keine aktuellen Preise abrufen. Anzeige nicht möglich.")
         # Optional: Show debug info
         # with st.expander("Fehlgeschlagene Preisabrufe"):
         #    st.write("Tagesdaten:", daily_prices)
         #    st.write("Aktuelle Preise:", current_prices)
         return

    current_owner_share_value = calculate_portfolio_value(
        PORTFOLIO_ASSETS, current_prices, INITIAL_CASH, ownership_percentage
    )
    # Calculate yesterday's value only if needed and possible
    yesterday_owner_share_value = 0.0 # Default
    if any(p is not None for p in yesterday_open_prices.values()):
        yesterday_owner_share_value = calculate_portfolio_value(
            PORTFOLIO_ASSETS, yesterday_open_prices, INITIAL_CASH, ownership_percentage
        )


    # --- 5. Display Key Metrics ---
    st.header("Portfolio Übersicht")
    col1, col2 = st.columns(2)

    with col1:
        delta_vs_baseline_str = ""
        if BASELINE_VALUE_FOR_DELTA is not None and BASELINE_VALUE_FOR_DELTA > 0:
             delta_vs_baseline = ((current_owner_share_value / BASELINE_VALUE_FOR_DELTA) - 1) * 100
             delta_vs_baseline_str = f"{delta_vs_baseline:.2f}% vs. €{BASELINE_VALUE_FOR_DELTA:,.0f}"

        st.metric(
            label="Aktueller Wert deines Anteils",
            value=f"€ {current_owner_share_value:,.2f}",
            delta=delta_vs_baseline_str if delta_vs_baseline_str else None,
            delta_color="off" # Baseline comparison is not a standard delta
        )

    with col2:
        # Calculate daily change only if both values are meaningful
        if yesterday_owner_share_value > 0 and current_owner_share_value > 0:
            delta_value_today = current_owner_share_value - yesterday_owner_share_value
            # Avoid division by zero, although yesterday_owner_share_value > 0 is checked
            delta_percent_today = (delta_value_today / yesterday_owner_share_value) * 100
            st.metric(
                label="Änderung seit Gestern Morgen",
                value=f"€ {delta_value_today:+,.2f}",
                delta=f"{delta_percent_today:+.2f}%"
                # delta_color automatically handles positive/negative
            )
        else:
            # Explain why delta is not available
            reason = "Keine Vortagsdaten" if yesterday_owner_share_value == 0 else "Aktueller Wert Null"
            st.metric(
                label="Änderung seit Gestern Morgen",
                value="N/A",
                delta=reason,
                delta_color="off"
            )

    # --- 6. Display Historical Performance Chart ---
    st.header("Portfolio Wertentwicklung (1 Jahr, Indexiert)")
    chart_placeholder = st.empty() # Use a placeholder for the chart area
    with st.spinner("Berechne historische Wertentwicklung..."):
        historical_share_value_df = calculate_historical_share_value(
            PORTFOLIO_ASSETS, historical_prices, ownership_percentage, INITIAL_CASH
        )

    # --- Plotting Logic ---
    if not historical_share_value_df.empty:
        try:
             # Ensure 'Date' is timezone-aware using the defined LOCAL_TZ
             if historical_share_value_df['Date'].dt.tz is None:
                 historical_share_value_df['Date'] = historical_share_value_df['Date'].dt.tz_localize('UTC').dt.tz_convert(LOCAL_TZ)
             else:
                 historical_share_value_df['Date'] = historical_share_value_df['Date'].dt.tz_convert(LOCAL_TZ)

             # Set 'Date' as index for charting
             historical_share_value_df = historical_share_value_df.set_index('Date')

             # Append current value as the latest point if it's more recent
             current_ts_local = pd.Timestamp.now(tz=LOCAL_TZ)
             last_historical_date = historical_share_value_df.index[-1]

             # Add current value only if it's significantly later than the last weekly point
             if current_ts_local > last_historical_date + timedelta(hours=1):
                 # Create a Series/row for the current value
                 latest_point = pd.DataFrame(
                     [current_owner_share_value],
                     columns=['Share Value'],
                     index=[current_ts_local]
                 )
                 # Ensure the index name matches if needed later, though not strictly required for concat
                 latest_point.index.name = 'Date'

                 # Concatenate (ignore_index=False keeps the DatetimeIndex)
                 historical_share_value_df = pd.concat([historical_share_value_df, latest_point])
                 historical_share_value_df = historical_share_value_df.sort_index() # Ensure order


             # Standardize the portfolio values: set the first value to 100
             first_value = historical_share_value_df["Share Value"].iloc[0]
             if first_value and first_value != 0:
                 historical_share_value_df["Wertentwicklung (Index)"] = (historical_share_value_df["Share Value"] / first_value) * 100

                 # Plot the indexed values
                 chart_placeholder.line_chart(
                     historical_share_value_df["Wertentwicklung (Index)"],
                     use_container_width=True
                 )
             else:
                 chart_placeholder.warning("Erster Wert im historischen Chart ist Null oder nicht vorhanden. Standardisierung nicht möglich. Zeige absolute Werte.")
                 chart_placeholder.line_chart(historical_share_value_df["Share Value"], use_container_width=True)

        except Exception as e:
             chart_placeholder.error(f"Fehler beim Erstellen des Charts: {e}")
             # Optionally show the raw data if chart fails
             # chart_placeholder.dataframe(historical_share_value_df)

    else:
        chart_placeholder.warning(f"Keine historischen Daten über dem Schwellenwert von €{HISTORICAL_VALUE_THRESHOLD:,.2f} verfügbar für den Chart.")


    # --- 7. Display Detailed Positions Table ---
    st.header("Detaillierte Positionen")
    table_placeholder = st.empty()
    with st.spinner("Berechne aktuelle Positionswerte und Tagesänderungen..."):
         positions_df = generate_positions_dataframe(
             PORTFOLIO_ASSETS, current_prices, yesterday_open_prices, INITIAL_CASH, ownership_percentage
         )

    # --- 8. Display Performance Highlights ---
    st.subheader("Highlights der Tagesperformance")
    highlights_placeholder = st.empty()
    top_performer_pct, top_performer_gain = find_top_performers(positions_df)

    if top_performer_pct or top_performer_gain:
         cols = highlights_placeholder.columns(2)
         with cols[0]:
             if top_performer_pct:
                 st.success(
                     f"🚀 **Höchste % Änderung:**\n"
                     f"**{top_performer_pct['name']}**: {top_performer_pct['value']:+.2f}%"
                 )
             else:
                  st.info("Keine prozentualen Tagesgewinner.")
         with cols[1]:
             if top_performer_gain:
                 st.success(
                      f"💰 **Höchster Gewinn (dein Anteil):**\n"
                      f"**{top_performer_gain['name']}**: € {top_performer_gain['value']:+,.2f}"
                 )
             else:
                  st.info("Keine absoluten Tagesgewinner.")
    else:
        highlights_placeholder.warning("⚠️ Keine Tagesperformance-Daten verfügbar.")


    # --- Display the main positions table ---
    if not positions_df.empty:
        table_placeholder.dataframe(
            positions_df[[ # Select and order columns for display
                "Name", "Menge", "Preis", "Wert", "% Anteil", "Tagesänderung (%)", "Gewinn für dich"
            ]].set_index("Name"), # Set Name as index for better readability
            # height=600, # Adjust height if needed, often auto-height is fine
            use_container_width=True,
            column_config={ # Optional: Customize column display
                 "Menge": st.column_config.NumberColumn(format="%d"),
                 "Preis": st.column_config.NumberColumn(format="€ %.2f"),
                 "Wert": st.column_config.NumberColumn(format="€ %.2f"),
                 "% Anteil": st.column_config.ProgressColumn(format="%.2f%%", min_value=0, max_value=max(1, positions_df["_numeric_share_pct"].max() if "_numeric_share_pct" in positions_df else 1)), # Add numeric share pct column if needed
                 "Tagesänderung (%)": st.column_config.NumberColumn(format="%.2f%%"),
                 "Gewinn für dich": st.column_config.NumberColumn(format="€ %+.2f"),
            }
        )
    else:
         table_placeholder.error("Positionsdaten konnten nicht generiert werden.")

    # --- Optional: Expander for Debugging Info ---
    with st.expander("Technische Details & Rohdaten (Debug)"):
         st.subheader("Abgerufene Tägliche Preise (letzte 5 Tage)")
         st.json({k: v.to_dict('records') if v is not None else None for k, v in daily_prices.items()}, expanded=False)
         st.subheader("Verarbeitete Preise")
         st.write("Aktuelle Schlusskurse:", current_prices)
         st.write("Vortag Öffnungskurse:", yesterday_open_prices)
         st.subheader("Generierte Positions-Tabelle (intern)")
         st.dataframe(positions_df, use_container_width=True)


if __name__ == "__main__":
    # Check if running in Streamlit requires specific setup (usually not needed)
    main()