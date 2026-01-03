import argparse
import os
import pandas as pd
import yfinance as yf
from datetime import timedelta


def detect_columns(df):
    cols = {c.lower(): c for c in df.columns}
    symbol_col = None
    date_col = None
    for name in ['symbol', 'stock', 'ticker']:
        if name in cols:
            symbol_col = cols[name]
            break
    for name in ['date', 'signal_date']:
        if name in cols:
            date_col = cols[name]
            break
    if symbol_col is None or date_col is None:
        raise ValueError('Could not detect symbol and date columns. Expected columns like "symbol" and "date"')
    return symbol_col, date_col


def get_prices(symbol, start, end):
    # Try multiple ticker variants (common for Indian tickers on Yahoo Finance)
    # prefer NSE/BSE suffixes for Indian tickers, then try raw symbol
    candidates = [symbol + '.NS', symbol + '.BO', symbol]
    for t in candidates:
        try:
            df = yf.download(t, start=start.strftime('%Y-%m-%d'), end=(end + timedelta(days=1)).strftime('%Y-%m-%d'), progress=False)
        except Exception:
            df = None
        if df is None or df.empty:
            continue
        df = df.sort_index()
        return df[['Close']]
    return None


def find_entry_exit(hist, signal_dt, days):
    # hist is df with DatetimeIndex
    hist_idx = hist.index
    # find first trading day on/after signal
    candidate = hist_idx[hist_idx >= signal_dt]
    if candidate.empty:
        return None, None, None, None
    entry_date = candidate[0]
    entry_pos = hist_idx.get_loc(entry_date)
    exit_pos = entry_pos + days
    if exit_pos >= len(hist_idx):
        return entry_date, hist.loc[entry_date, 'Close'], None, None
    exit_date = hist_idx[exit_pos]
    return entry_date, hist.loc[entry_date, 'Close'], exit_date, hist.loc[exit_date, 'Close']


def run_backtest(signals_path, investment, days, output_path):
    sigs = pd.read_csv(signals_path)
    symbol_col, date_col = detect_columns(sigs)
    # many exported scanners use DD-MM-YYYY — parse with dayfirst=True
    sigs[date_col] = pd.to_datetime(sigs[date_col], dayfirst=True)

    results = []
    cache = {}

    for _, row in sigs.iterrows():
        symbol = str(row[symbol_col]).strip()
        sig_dt = row[date_col].to_pydatetime()
        print(f"Processing {symbol} on {sig_dt.date()}")
        if symbol not in cache:
            # download a reasonable range around the earliest and latest dates
            cache[symbol] = None
        # ensure we have prices covering this signal → download if missing or too small
        # download window: signal date -> signal date + days + 10 to be safe
        start = sig_dt - timedelta(days=1)
        end = sig_dt + timedelta(days=days + 3)
        hist = get_prices(symbol, start, end)
        if hist is None:
            results.append({
                'symbol': symbol,
                'signal_date': sig_dt.date(),
                'entry_date': None,
                'entry_price': None,
                'exit_date': None,
                'exit_price': None,
                'return_pct': None,
                'profit': None,
                'investment': investment,
                'note': 'no price data'
            })
            continue

        entry_date, entry_price, exit_date, exit_price = find_entry_exit(hist, sig_dt, days)
        if entry_price is None:
            note = 'no entry'
            ret = None
            profit = None
        elif exit_price is None:
            note = 'no exit (insufficient data)'
            ret = None
            profit = None
        else:
            ret = (exit_price - entry_price) / entry_price
            profit = ret * investment
            note = ''

        results.append({
            'symbol': symbol,
            'signal_date': sig_dt.date(),
            'entry_date': getattr(entry_date, 'date', lambda: None)() if entry_date is not None else None,
            'entry_price': float(entry_price) if entry_price is not None else None,
            'exit_date': getattr(exit_date, 'date', lambda: None)() if exit_date is not None else None,
            'exit_price': float(exit_price) if exit_price is not None else None,
            'return_pct': float(ret) if ret is not None else None,
            'profit': float(profit) if profit is not None else None,
            'investment': investment,
            'note': note
        })

    out_df = pd.DataFrame(results)
    out_df.to_csv(output_path, index=False)
    print(f"Saved results to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Simple 1-leg backtest: entry on signal date, exit after N trading days')
    parser.add_argument('--signals', required=True, help='CSV file with signal rows (columns: symbol and date)')
    parser.add_argument('--investment', type=float, default=1000.0, help='Amount invested per trade')
    parser.add_argument('--days', type=int, default=5, help='Number of trading days to hold')
    parser.add_argument('--output', default='backtest_results.csv', help='Output CSV file')
    args = parser.parse_args()

    if not os.path.exists(args.signals):
        raise SystemExit(f"Signals file not found: {args.signals}")

    run_backtest(args.signals, args.investment, args.days, args.output)


if __name__ == '__main__':
    main()
