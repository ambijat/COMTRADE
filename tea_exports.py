#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UN Comtrade – Tea (HS 0902) Exports → CSV + MA(3) snapshots

Outputs:
  - out/tea_exports_comtrade.csv
      columns: reporter, year, trade_value_usd
  - out/tea_exports_top10_ma3_snapshots.csv
      columns: year, reporter, ma3_usd

Run:
  python tea_exports_pipeline.py --years 1962:2025 --reporters All --partner 0
Environment:
  COMTRADE_API_KEY=...   # optional; if absent, uses preview endpoints
"""

import os, sys, time, argparse
from typing import Iterable, List, Optional, Union
import pandas as pd

# ---- paste your key here if you like (leave "" if using CLI/env) ----
API_KEY = "3d88e27040194170b1e750b17e88fe38"  # e.g., "xxxxxxxxxxxxxxxxxxxxxxxx"

# -------- deps --------
try:
    import comtradeapicall
except Exception as e:
    sys.stderr.write(
        "\nMissing dependency: comtradeapicall\n"
        "In PyCharm: Settings → Project → Python Interpreter → + → comtradeapicall\n"
        "Or in terminal of your PyCharm venv: pip install comtradeapicall pandas\n"
    )
    raise

# -------- helpers --------
def chunks(seq: List[int], size: int) -> Iterable[List[int]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]

def parse_years(years: str) -> List[int]:
    """Accept '1962:2025' or '1962,1967,1972'."""
    years = years.strip()
    if ":" in years:
        a, b = years.split(":")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in years.split(",") if x.strip()]

def _call_comtrade(period: str, reporters: str, partner: str,
                   api_key: Optional[str], use_tariffline: bool,
                   proxy_url: Optional[str]):
    cmd = "0902"  # HS-4 Tea
    # comtrade API expects "all" (lowercase) for all reporters
    rep = "all" if str(reporters).strip().lower() == "all" else reporters

    if api_key:  # authenticated → /data (final)
        if use_tariffline:
            return comtradeapicall.getTarifflineData(
                api_key, typeCode="C", freqCode="A", clCode="HS",
                period=period, reporterCode=rep, cmdCode=cmd,
                flowCode="X", partnerCode=partner,
                maxRecords=500000, format_output="JSON",
                includeDesc=True, proxy_url=proxy_url
            )
        return comtradeapicall.getFinalData(
            api_key, typeCode="C", freqCode="A", clCode="HS",
            period=period, reporterCode=rep, cmdCode=cmd,
            flowCode="X", partnerCode=partner,
            maxRecords=500000, format_output="JSON",
            includeDesc=True, proxy_url=proxy_url
        )

    # preview endpoints (your package version requires these 3 extra params)
    if use_tariffline:
        return comtradeapicall.previewTarifflineData(
            typeCode="C", freqCode="A", clCode="HS",
            period=period, reporterCode=rep, cmdCode=cmd,
            flowCode="X", partnerCode=partner,
            partner2Code=None, customsCode=None, motCode=None,
            maxRecords=20000, format_output="JSON",
            countOnly=None, includeDesc=True, proxy_url=proxy_url
        )
    return comtradeapicall.previewFinalData(
        typeCode="C", freqCode="A", clCode="HS",
        period=period, reporterCode=rep, cmdCode=cmd,
        flowCode="X", partnerCode=partner,
        partner2Code=None, customsCode=None, motCode=None,
        maxRecords=20000, format_output="JSON",
        aggregateBy=None, breakdownMode="classic",
        countOnly=None, includeDesc=True, proxy_url=proxy_url
    )

def download_tea_exports(years: Union[str, List[int]] = "1962:2025",
                         reporters: str = "All",
                         partner: str = "0",
                         api_key: Optional[str] = None,
                         proxy_url: Optional[str] = None,
                         throttle_s: float = 1.2,
                         use_tariffline: bool = False) -> pd.DataFrame:
    """Return tidy df: reporter, year, trade_value_usd."""
    # normalize years → list[int]
    def parse_years(s: str) -> List[int]:
        s = s.strip()
        if ":" in s:
            a, b = s.split(":")
            return list(range(int(a), int(b) + 1))
        return [int(x) for x in s.split(",") if x.strip()]

    if isinstance(years, str):
        years = parse_years(years)

    years = sorted(set(int(y) for y in years))
    # chunk to 10-year blocks, but pass each block as a comma list
    frames = []
    for i in range(0, len(years), 10):
        block = years[i:i+10]
        period = ",".join(str(y) for y in block)  # <-- key change
        df = _call_comtrade(period, reporters, partner, api_key, use_tariffline, proxy_url)
        if df is not None and len(df):
            frames.append(df)
        time.sleep(throttle_s)

    if not frames:
        raise RuntimeError(
            f"No data returned. Check parameters: reporters='{reporters}', "
            f"partner='{partner}', years={years[:3]}…{years[-3:]}, "
            f"API key detected={bool(api_key)}."
        )

    out = pd.concat(frames, ignore_index=True).dropna(subset=["trade_value_usd"])
    out = out.groupby(["reporter","year"], as_index=False)["trade_value_usd"].sum()
    return out

def make_snapshots_top10_ma3(trade: pd.DataFrame, step: int = 5) -> pd.DataFrame:
    """Return Top-10 by MA(3) for snapshot years 1962, 1967, …"""
    trade = trade.sort_values(["reporter","year"])
    trade["ma3_usd"] = (trade
                        .groupby("reporter")["trade_value_usd"]
                        .transform(lambda s: s.rolling(3, min_periods=3).mean()))
    if trade["year"].empty:
        return pd.DataFrame(columns=["year","reporter","ma3_usd"])
    y0 = 1962
    y_max = int(trade["year"].max())
    snaps = list(range(y0, y_max + 1, step))
    rows = []
    for y in snaps:
        snap = trade[(trade["year"] == y) & trade["ma3_usd"].notna()]
        if len(snap):
            for _, r in snap.nlargest(10, "ma3_usd").iterrows():
                rows.append({"year": y, "reporter": r["reporter"], "ma3_usd": r["ma3_usd"]})
    return pd.DataFrame(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="1962:2025",
                    help="e.g., 1962:2025 or 2000,2005,2010")
    ap.add_argument("--reporters", default="All",
                    help="'All' or comma list of ISO3/codes (e.g., IND,LKA,CHN)")
    ap.add_argument("--partner", default="0", help="0 = World")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--proxy", default=None)
    ap.add_argument("--use-tariffline", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    api_key = os.environ.get("COMTRADE_API_KEY")

    print("Downloading…")
    df = download_tea_exports(
        years=args.years,
        reporters=args.reporters,
        partner=args.partner,
        api_key=api_key,
        proxy_url=args.proxy,
        use_tariffline=args.use_tariffline,
    )

    csv1 = os.path.join(args.outdir, "tea_exports_comtrade.csv")
    df.to_csv(csv1, index=False)
    print(f"Saved: {csv1}  ({len(df):,} rows)")

    snaps = make_snapshots_top10_ma3(df)
    csv2 = os.path.join(args.outdir, "tea_exports_top10_ma3_snapshots.csv")
    snaps.to_csv(csv2, index=False)
    print(f"Saved: {csv2}  ({len(snaps):,} rows)")

if __name__ == "__main__":
    main()

