import io
from datetime import timedelta

import pandas as pd
import streamlit as st
import yfinance as yf


@st.cache_data
def get_prices_cached(ticker, start, end):
    try:
        df = yf.download(ticker, start=start.strftime('%Y-%m-%d'), end=(end + timedelta(days=1)).strftime('%Y-%m-%d'), progress=False)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    return df.sort_index()[['Close']]


def get_prices_for_symbol(symbol, start, end):
    # Try NSE/BSE variants first for Indian tickers
    candidates = [f"{symbol}.NS", f"{symbol}.BO", symbol]
    for t in candidates:
        df = get_prices_cached(t, start, end)
        if df is not None:
            return df, t
    return None, None


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
    return symbol_col, date_col


def find_entry_exit(hist, signal_dt, days):
    hist_idx = hist.index
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


def format_results(df):
    if 'entry_price' in df:
        df['entry_price'] = df['entry_price'].apply(lambda v: ("{:.2f}".format(v)) if pd.notnull(v) else '')
    if 'exit_price' in df:
        df['exit_price'] = df['exit_price'].apply(lambda v: ("{:.2f}".format(v)) if pd.notnull(v) else '')
    if 'profit' in df:
        df['profit'] = df['profit'].apply(lambda v: ("{:.2f}".format(v)) if pd.notnull(v) else '')
    if 'investment' in df:
        df['investment'] = df['investment'].apply(lambda v: ("{:.2f}".format(v)) if pd.notnull(v) else '')
    if 'return_pct' in df:
        def fmt_pct(v):
            if pd.isnull(v):
                return ''
            fv = float(v)
            if abs(fv) < 2:
                pct = fv * 100
            else:
                pct = fv
            return "{:.2f}%".format(pct)
        df['return_pct'] = df['return_pct'].apply(fmt_pct)
    return df


def run_backtest_df(signals_df, investment, days, show_progress=False):
    symbol_col, date_col = detect_columns(signals_df)
    if symbol_col is None or date_col is None:
        raise st.error('Could not detect symbol/date columns in uploaded CSV. Ensure columns named `symbol` and `date` exist.')
    signals_df[date_col] = pd.to_datetime(signals_df[date_col], dayfirst=True)

    results = []
    total = len(signals_df)
    progress = st.progress(0) if show_progress else None
    for i, row in signals_df.iterrows():
        symbol = str(row[symbol_col]).strip()
        sig_dt = row[date_col].to_pydatetime()
        start = sig_dt - timedelta(days=1)
        end = sig_dt + timedelta(days=days + 3)
        hist, used = get_prices_for_symbol(symbol, start, end)
        if hist is None:
            results.append({'symbol': symbol, 'signal_date': sig_dt.date(), 'entry_date': None, 'entry_price': None, 'exit_date': None, 'exit_price': None, 'return_pct': None, 'profit': None, 'investment': investment, 'note': 'no price data'})
        else:
            entry_date, entry_price, exit_date, exit_price = find_entry_exit(hist, sig_dt, days)
            if entry_price is None:
                results.append({'symbol': symbol, 'signal_date': sig_dt.date(), 'entry_date': None, 'entry_price': None, 'exit_date': None, 'exit_price': None, 'return_pct': None, 'profit': None, 'investment': investment, 'note': 'no entry'})
            elif exit_price is None:
                results.append({'symbol': symbol, 'signal_date': sig_dt.date(), 'entry_date': entry_date.date(), 'entry_price': float(entry_price), 'exit_date': None, 'exit_price': None, 'return_pct': None, 'profit': None, 'investment': investment, 'note': 'no exit (insufficient data)'})
            else:
                ret = (float(exit_price) - float(entry_price)) / float(entry_price)
                profit = ret * investment
                results.append({'symbol': symbol, 'signal_date': sig_dt.date(), 'entry_date': entry_date.date(), 'entry_price': float(entry_price), 'exit_date': exit_date.date(), 'exit_price': float(exit_price), 'return_pct': float(ret), 'profit': float(profit), 'investment': investment, 'note': ''})
        if progress:
            progress.progress(int((i + 1) / total * 100))

    out_df = pd.DataFrame(results)
    return out_df


def main():
    st.title('Simple Backtest — Entry on signal date, exit after N trading days')
    st.markdown('Upload a CSV with `symbol` and `date` columns (DD-MM-YYYY).')

    uploaded = st.file_uploader('Upload signals CSV', type=['csv'])
    investment = st.number_input('Investment per trade', value=1000.0, step=100.0)
    days = st.number_input('Hold for trading days', min_value=1, value=5, step=1)

    if uploaded is not None:
        try:
            sigs = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f'Could not read uploaded CSV: {e}')
            return
        if st.button('Run Backtest'):
            with st.spinner('Running backtest — this may take some time...'):
                out = run_backtest_df(sigs, investment, int(days), show_progress=True)
                out_fmt = format_results(out.copy())
                st.success('Backtest complete')
                st.dataframe(out_fmt)
                csv_bytes = out_fmt.to_csv(index=False).encode('utf-8')
                st.download_button('Download results CSV', data=csv_bytes, file_name='backtest_results.csv', mime='text/csv')


if __name__ == '__main__':
    main()
