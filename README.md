# Simple 5-day backtest

Usage:

1. Place a CSV file with one row per signal. The CSV must contain columns named `symbol` (or `stock`/`ticker`) and `date` (or `signal_date`). Example:

symbol,date
AAPL,2025-12-01
MSFT,2025-12-02

2. Run the script:

```bash
python backtest.py --signals path/to/signals.csv --investment 1000 --days 5 --output results.csv
```

3. Output `results.csv` will contain entry/exit dates, prices, return and profit per trade.

Notes:
- The script uses `yfinance` to download historical daily Close prices.
- Entry price is the first available trading-day close on or after the signal date.
- Exit price is the close after `--days` trading days following the entry.
- If there is insufficient price history for exit, the row will be marked accordingly.
