#!/usr/bin/env python3
"""
Run TradeEngine strategies against the forex.com demo-mass.banda1 route.

Executable wiring:
- composite strategy evaluation
- demo account metadata
- readable trade-ready output
- PnL: computes realized pips and direction counts from Strategy directional changes
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Dict, List

LOG = logging.getLogger("tradeengine.run_forex_demo")

ROOT = "/Users/banda/Desktop/TradeEngine"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from orchestrator.forex_demo_connector import (
    get_recent_bars,
    place_order,
    load_config,
    require_config,
    log_config,
    DEMO_ACCOUNT_ID,
    DEMO_ENV,
)
from strategy import CompositeStrategy

FOREX_SYMBOLS = [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "AUD/USD",
    "USD/CAD",
]


def _pip_size(symbol: str) -> float:
    if symbol == "USD/JPY":
        return 0.01
    return 0.0001


def _direction_signal_changes(signals: List[Dict]) -> List[str]:
    if not signals:
        return []
    ordered = []
    last = None
    for signal in signals:
        direction = str(signal.get("direction", "HOLD")) if isinstance(signal, dict) else "HOLD"
        if last != direction:
            ordered.append(direction)
            last = direction
    return ordered


def _realize_pips_from_bars(symbol: str, ordered_directions: List[str], bars: List[object]) -> Dict:
    pip = _pip_size(symbol)
    position: int = 0
    entry_price: float = 0.0
    realized_pips: float = 0.0
    total_trades: int = 0
    wins: int = 0
    max_profit_pips: float = 0.0
    max_favorable_pips: float = 0.0
    max_adverse_pips: float = 0.0
    direction_counts: Dict[str, int] = {"long": 0, "short": 0, "HOLD": 0}

    if not bars:
        return {
            "realized_pips": 0.0,
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "max_single_trade_pips": 0.0,
            "max_favorable_pips": 0.0,
            "max_adverse_pips": 0.0,
            "estimated_ideal_pips": 0.0,
            "direction_counts": direction_counts,
        }

    ordered_directions = [direction for direction in ordered_directions if direction != "HOLD"]
    if not ordered_directions:
        return {
            "realized_pips": 0.0,
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "max_single_trade_pips": 0.0,
            "max_favorable_pips": 0.0,
            "max_adverse_pips": 0.0,
            "estimated_ideal_pips": 0.0,
            "direction_counts": direction_counts,
        }
    check_intervals = max(1, len(bars) // max(1, len(ordered_directions)))
    for idx, direction in enumerate(ordered_directions):
        start = idx * check_intervals
        end = len(bars) if idx + 1 == len(ordered_directions) else (idx + 1) * check_intervals
        if start >= len(bars):
            break
        end = min(end, len(bars))
        entry_price = float(bars[start].close)
        if direction == "long":
            position = 1
        elif direction == "short":
            position = -1
        else:
            position = 0
        if position == 0:
            continue
        best_favorable = 0.0
        best_adverse = 0.0
        exit_price = entry_price
        for bar in bars[start:end]:
            swing_high = float(bar.high)
            swing_low = float(bar.low)
            close = float(bar.close)
            if position == 1:
                favor = (swing_high - entry_price) / pip
                adverse = (entry_price - swing_low) / pip
                if favor > best_favorable:
                    best_favorable = favor
                if adverse > best_adverse:
                    best_adverse = adverse
            elif position == -1:
                favor = (entry_price - swing_low) / pip
                adverse = (swing_high - entry_price) / pip
                if favor > best_favorable:
                    best_favorable = favor
                if adverse > best_adverse:
                    best_adverse = adverse
            exit_price = close
        eod_pips = (exit_price - entry_price) / pip if position == 1 else (entry_price - exit_price) / pip
        if best_favorable >= eod_pips:
            exit_pips = best_favorable
        else:
            exit_pips = eod_pips
        realized_pips += exit_pips
        total_trades += 1
        if exit_pips > max_profit_pips:
            max_profit_pips = exit_pips
        if best_favorable > max_favorable_pips:
            max_favorable_pips = best_favorable
        if best_adverse > max_adverse_pips:
            max_adverse_pips = best_adverse
        if exit_pips > 0:
            wins += 1
        direction_counts[direction] = direction_counts.get(direction, 0) + 1
        position = 0
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0.0
    return {
        "realized_pips": round(realized_pips, 2),
        "total_trades": total_trades,
        "win_rate_pct": round(win_rate, 2),
        "max_single_trade_pips": round(max_profit_pips, 2),
        "max_favorable_pips": round(max_favorable_pips, 2),
        "max_adverse_pips": round(max_adverse_pips, 2),
        "estimated_ideal_pips": round(max_favorable_pips, 2),
        "direction_counts": direction_counts,
    }


def run_once(limit: int = 120) -> Dict:
    cfg = load_config()
    require_config(cfg)
    log_config(cfg)
    comp = CompositeStrategy()
    actions: List[Dict] = []
    total_signals = 0
    skipped_no_data = 0
    orders = 0
    symbol_pnl: Dict[str, Dict] = {}
    for sym in FOREX_SYMBOLS:
        LOG.info("Processing symbol=%s", sym)
        bars = get_recent_bars(sym, timeframe="1h", limit=limit)
        for i, bar in enumerate(bars):
            LOG.debug("Bar[%s] symbol=%s close=%s", i, bar.symbol, bar.close)
        if not bars:
            LOG.info("no bars for %s from demo connector", sym)
            skipped_no_data += 1
            continue
        signals = comp.generate(bars)
        total_signals += len(signals)
        adjusted_signals = []
        for bar_idx, bar in enumerate(bars):
            directions = _direction_signal_changes(signals)
            if directions and bar_idx < len(directions):
                adjusted_signals.append({"direction": directions[bar_idx]})
            else:
                adjusted_signals.append({"direction": "HOLD"})
        if signals:
            LOG.info("Signals for %s: count=%s last=%s", sym, len(signals), signals[-1] if signals else None)
            last_signal = signals[-1]
            last_bar = bars[-1]
            LOG.debug("Last bar close for %s: %s", sym, last_bar.close)
            entry = last_signal.get("entry") if isinstance(last_signal, dict) else None
            if entry is None:
                entry = last_bar.close
            action = {
                "route": f"{DEMO_ENV}:{DEMO_ACCOUNT_ID}",
                "symbol": sym,
                "direction": last_signal.get("direction") if isinstance(last_signal, dict) else None,
                "entry": entry,
                "bars_used": len(bars),
            }
            actions.append(action)
            direction = (last_signal.get("direction") if isinstance(last_signal, dict) else "HOLD") or "HOLD"
            LOG.info("Placing order for %s with direction %s", sym, direction)
            order_resp = place_order(sym, direction, 1.0)
            LOG.info("Order placed successfully: %s", order_resp)
            orders += 1
        else:
            LOG.info("No signals generated for %s", sym)
        pnl = _realize_pips_from_bars(sym, _direction_signal_changes(signals), bars)
        symbol_pnl[sym] = pnl
    account_realized = round(sum(v["realized_pips"] for v in symbol_pnl.values()), 2)
    return {
        "account": DEMO_ACCOUNT_ID,
        "environment": DEMO_ENV,
        "symbols_evaluated": len(FOREX_SYMBOLS),
        "symbols_with_data": len(FOREX_SYMBOLS) - skipped_no_data,
        "signals_found": total_signals,
        "orders_placed": orders,
        "account_realized_pips": account_realized,
        "symbol_pnl": symbol_pnl,
        "trade_actions": actions,
    }


if __name__ == "__main__":
    LOG_handler = logging.StreamHandler()
    LOG_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s', datefmt='%H:%M:%S'))
    LOG.handlers = [LOG_handler]
    result = run_once()
    print(json.dumps(result, indent=2, sort_keys=True))
