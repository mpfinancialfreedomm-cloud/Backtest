import argparse
import pandas as pd


def format_csv(path_in, path_out=None):
    df = pd.read_csv(path_in)
    # Columns we expect: entry_price, exit_price, return_pct, profit, investment
    if 'entry_price' in df.columns:
        df['entry_price'] = df['entry_price'].apply(lambda v: ("{:.2f}".format(v)) if pd.notnull(v) else '')
    if 'exit_price' in df.columns:
        df['exit_price'] = df['exit_price'].apply(lambda v: ("{:.2f}".format(v)) if pd.notnull(v) else '')
    if 'profit' in df.columns:
        df['profit'] = df['profit'].apply(lambda v: ("{:.2f}".format(v)) if pd.notnull(v) else '')
    if 'investment' in df.columns:
        df['investment'] = df['investment'].apply(lambda v: ("{:.2f}".format(v)) if pd.notnull(v) else '')
    if 'return_pct' in df.columns:
        def fmt_pct(v):
            if pd.isnull(v):
                return ''
            try:
                # if value already like 0.01 or 1.0 (fraction), determine magnitude
                fv = float(v)
            except Exception:
                return v
            # if abs less than 2, assume it's a fraction (e.g., 0.01 -> 1.00%) else if >2 treat as already percentage
            if abs(fv) < 2:
                pct = fv * 100
            else:
                pct = fv
            return "{:.2f}%".format(pct)

        df['return_pct'] = df['return_pct'].apply(fmt_pct)

    out = path_out or path_in
    df.to_csv(out, index=False)
    print(f"Written formatted CSV to {out}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('input')
    p.add_argument('--output', '-o', help='Output file (defaults to overwrite input)')
    args = p.parse_args()
    format_csv(args.input, args.output)


if __name__ == '__main__':
    main()
