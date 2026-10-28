#!/usr/bin/env python3
"""A股沪深月线MACD选股：只发布已完成月份的确认金叉。"""
import argparse
import json
import logging
import math
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import baostock as bs
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "results.json"
LOG = logging.getLogger("screen")
SH = ("600", "601", "603", "605", "688", "689")
SZ = ("000", "001", "002", "003", "300", "301")

def rows(result):
    if result.error_code != "0":
        raise RuntimeError(f"BaoStock: {result.error_code} {result.error_msg}")
    out = []
    while result.next():
        out.append(dict(zip(result.fields, result.get_row_data())))
    return out

def is_a_share(code):
    if re.fullmatch(r"sh\.\d{6}", code):
        return code[3:].startswith(SH)
    if re.fullmatch(r"sz\.\d{6}", code):
        return code[3:].startswith(SZ)
    return False

def available_name(name):
    s = name.strip().upper().replace(" ", "")
    return bool(s) and not s.startswith(("ST", "*ST")) and "退" not in s

def universe():
    u = [
        {"code": r["code"], "name": r["code_name"]}
        for r in rows(bs.query_stock_basic())
        if r.get("type") == "1" and r.get("status") == "1"
        and is_a_share(r.get("code", ""))
        and available_name(r.get("code_name", ""))
    ]
    if len(u) < 100:
        raise RuntimeError(f"证券池不足：{len(u)}，终止发布")
    return sorted(u, key=lambda x: x["code"])

def monthly_bars(code, now):
    rs = bs.query_history_k_data_plus(
        code, "date,code,close,volume,amount",
        start_date="2016-01-01", end_date=now.strftime("%Y-%m-%d"),
        frequency="m", adjustflag="2")
    bars = []
    month = now.strftime("%Y-%m")
    for r in rows(rs):
        if r.get("date", "")[:7] >= month:
            continue  # 正在进行的月份不能被判作确认金叉
        try:
            c = float(r["close"])
            if math.isfinite(c) and c > 0:
                bars.append({"date": r["date"], "close": c})
        except (TypeError, ValueError, KeyError):
            continue
    return bars

def macd_signal(bars):
    if len(bars) < 40:
        return None
    close = pd.Series([x["close"] for x in bars], dtype="float64")
    dif = close.ewm(span=10, adjust=False).mean() - close.ewm(span=22, adjust=False).mean()
    dea = dif.ewm(span=8, adjust=False).mean()
    crosses = [i for i in range(1, len(close))
               if dif.iloc[i-1] <= dea.iloc[i-1] and dif.iloc[i] > dea.iloc[i]]
    if not crosses:
        return None
    i = crosses[-1]
    age = len(close) - 1 - i
    if age > 2 or dif.iloc[-1] <= dea.iloc[-1]:
        return None
    recent = close.tail(36)
    low, high, last = float(recent.min()), float(recent.max()), float(close.iloc[-1])
    position = (last - low)/(high-low) if high > low else 0.5
    ret = 100 * (last / float(close.iloc[-13]) - 1)
    below = bool(dif.iloc[i] <= 0)
    score = 25 + (25 if below else 0) + (20 if position <= 0.35 else 10 if position <= 0.6 else 0) + (15 if ret <= 40 else 0) + (15-5*age)
    return {
        "cross_month": bars[i]["date"][:7],
        "last_bar_month": bars[-1]["date"][:7],
        "months_since_cross": age,
        "close": round(last, 3),
        "dif": round(float(dif.iloc[-1]), 5),
        "dea": round(float(dea.iloc[-1]), 5),
        "macd_histogram": round(float(2 * (dif.iloc[-1] - dea.iloc[-1])), 5),
        "cross_below_zero": below,
        "range36_position_pct": round(position * 100, 1),
        "return12_pct": round(ret, 1),
        "technical_score": score,
    }

def scan(max_stocks=0, delay=0.0):
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"BaoStock login failed: {lg.error_msg}")
    try:
        stocklist = universe()
        total = len(stocklist)
        if max_stocks:
            stocklist = stocklist[:max_stocks]
        matches, failures, data_count = [], [], 0
        for k, stock in enumerate(stocklist, 1):
            try:
                bars = monthly_bars(stock["code"], now)
                if len(bars) >= 40:
                    data_count += 1
                result = macd_signal(bars)
                if result:
                    matches.append({**stock, "symbol": stock["code"][3:], **result})
            except Exception as exc:
                failures.append({"code": stock["code"], "error": str(exc)[:150]})
                if len(failures) <= 10:
                    LOG.warning("Query failed for %s: %s", stock["code"], exc)
            if k % 100 == 0:
                LOG.info("Processed %s/%s, matches %s, errors %s", k, len(stocklist), len(matches), len(failures))
            if delay:
                time.sleep(delay)
        if data_count < max(1, int(len(stocklist) * .80)):
            raise RuntimeError(f"数据覆盖不足 {data_count}/{len(stocklist)}，拒绝发布")
        matches.sort(key=lambda x: (-x["technical_score"], x["months_since_cross"], x["code"]))
        return {
            "generated_at_china": now.strftime("%Y-%m-%d %H:%M:%S"),
            "effective_date": now.strftime("%Y-%m-%d"),
            "scope": "沪深A股（不含北交所），剔除ST及退市名称",
            "indicator": "月MACD(10,22,8)，最近3个已完成月线确认金叉且DIF>DEA",
            "macd_parameters": {"fast": 10, "slow": 22, "signal": 8},
            "price_adjustment": "BaoStock前复权；与其他软件可能有差异",
            "is_full_market_run": max_stocks == 0,
            "universe_size": total,
            "stock_count_scanned": len(stocklist),
            "monthly_data_count": data_count,
            "failed_count": len(failures),
            "failed_sample": failures[:25],
            "count": len(matches),
            "stocks": matches,
            "warnings": ["仅技术面观察排序，未筛盈利、估值、国资背景、社保持仓。", "不能把金叉当作买入建议。"],
        }
    finally:
        bs.logout()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-stocks", type=int, default=0)
    parser.add_argument("--delay", type=float, default=0)
    args = parser.parse_args()
    if args.max_stocks < 0 or args.delay < 0:
        parser.error("max-stocks和delay必须非负")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    report = scan(args.max_stocks, args.delay)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(OUT)
    LOG.info("Saved %s matches: %s", report["count"], OUT)

if __name__ == "__main__":
    main()
