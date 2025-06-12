# Project Anni

This repository contains various Streamlit apps and data scripts for portfolio tracking. The applications depend on a few Python packages such as Streamlit, pandas, yfinance, and pytz.

## Updating dependencies

1. Review all Python files for imports to determine which third-party packages are used. The main packages currently required are `streamlit`, `pandas`, `yfinance`, and `pytz`.
2. Update `requirements.txt` with pinned versions. To discover the latest versions available on PyPI, run:
   ```bash
   pip index versions PACKAGE_NAME
   ```
   Replace `PACKAGE_NAME` with the package you want to check. Edit `requirements.txt` and pin each package using the `==` operator.
3. After editing `requirements.txt`, install the dependencies locally:
   ```bash
   pip install -r requirements.txt
   ```
4. Run any test scripts (for example `python -m py_compile *.py`) to verify that the code still works with the new package versions.

