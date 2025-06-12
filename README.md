# Portfolio Tracker

This repository contains several Streamlit apps used to track a family investment portfolio. Each app focuses on different participants or views of the portfolio and relies on the same dataset of stock holdings.

## Setup

Use Python 3 and install the required packages with:

```bash
python -m pip install -r requirements.txt
```

## Running the Apps

Execute any of the following Streamlit scripts to start a web interface:

```bash
streamlit run streamlit_app.py           # full portfolio tracker
streamlit run annika_only_depot.py       # Annika's share only
streamlit run christian_only_depot.py    # Christian's share only
streamlit run parents_depot_only.py      # Parents' share only
streamlit run Annika1.py                 # minimal example for Annika
streamlit run test_dep.py                # experimental tracker
```

## Data Files

The `*_data.json` files store persistent information for the apps:

- `annika_data.json`, `christian_data.json`, `parents_data.json` – saved ownership percentages and transactions for each participant.
- `portfolio_data.json` – aggregated ownership data and transaction history used by `streamlit_app.py`.

These files are automatically read and updated by the applications to maintain portfolio state across runs.
