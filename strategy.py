#!/usr/bin/env python3
"""
Strategy module for TradeEngine.
Includes:
  - MomentumCross: EMA crossover with RSI filter
  - BreakoutPull: Donchian breakout with volume filter
  - SMACross: Simple MA crossover with trend filter (more robust)
"""
from typing import List, Dict, Optional
import statistics

def sma(values: List[float], period: int) -> List[Optional[float]]:
  out: List[Optional[float]] = []
  for i in range(len(values)):
    if i < period - 1:
      out.append(None)
      continue
    out.append(statistics.fmean(values[i-period+1:i+1]))
  return out

def rsi(values: List[float], period: int = 14) -> List[Optional[float]]:
  out: List[Optional[float]] = []
  gains: List[float] = []
  losses: List[float] = []
  for i in range(1, len(values)):
    delta = values[i] - values[i-1]
    gains.append(max(0.0, delta))
    losses.append(max(0.0, -delta))
  for i in range(len(gains)):
    if i < period - 1:
      out.append(None)
      continue
    avg_g = statistics.fmean(gains[i-period+1:i+1])
    avg_l = statistics.fmean(losses[i-period+1:i+1])
    if avg_l == 0:
      out.append(100.0)
    else:
      rs = avg_g / avg_l
      out.append(100 - (100 / (1 + rs)))
  return out

class Strategy:
  name: str = 'base'
  def generate(self, bars: List[Dict]) -> List[Dict]:
    raise NotImplementedError

class MomentumCross(Strategy):
  name = 'momentum_cross'
  def generate(self, bars: List[Dict]) -> List[Dict]:
    closes = [b['close'] for b in bars]
    fast = sma(closes, 8)
    slow = sma(closes, 21)
    r = rsi(closes, 14)
    signals: List[Dict] = []
    for i in range(1, len(bars)):
      if i >= len(fast) or i >= len(slow) or i >= len(r):
        break
      if fast[i] is None or slow[i] is None or r[i] is None or fast[i-1] is None or slow[i-1] is None:
        continue
      if fast[i] > slow[i] and fast[i-1] <= slow[i-1] and r[i] < 70:
        signals.append({'symbol': bars[i].get('symbol',''), 'direction': 'long', 'timeframe': bars[i].get('timeframe','1h'), 'entry': closes[i], 'time': bars[i].get('ts')})
      elif fast[i] < slow[i] and fast[i-1] >= slow[i-1] and r[i] > 30:
        signals.append({'symbol': bars[i].get('symbol',''), 'direction': 'short', 'timeframe': bars[i].get('timeframe','1h'), 'entry': closes[i], 'time': bars[i].get('ts')})
    return signals

class BreakoutPull(Strategy):
  name = 'breakout_pull'
  def generate(self, bars: List[Dict]) -> List[Dict]:
    lookback = 20
    signals: List[Dict] = []
    if len(bars) < lookback + 1:
      return signals
    closes = [b['close'] for b in bars if b.get('close') is not None]
    highs = [b['high'] for b in bars if b.get('high') is not None]
    lows = [b['low'] for b in bars if b.get('low') is not None]
    volumes = [b.get('volume') or 0 for b in bars]
    valid = [i for i in range(len(bars)) if closes[i] is not None and highs[i] is not None and lows[i] is not None]
    if len(valid) < lookback + 1:
      return signals
    for idx_pos in range(lookback, len(valid)):
      i = valid[idx_pos]
      prev_indices = valid[max(0, idx_pos - lookback):idx_pos]
      if len(prev_indices) < lookback:
        continue
      prev_high = max(highs[j] for j in prev_indices)
      prev_low = min(lows[j] for j in prev_indices)
      price = closes[i]
      vol = volumes[i]
      avg_vol = sum(volumes[j] for j in prev_indices) / len(prev_indices)
      if avg_vol <= 0:
        avg_vol = 1.0
      if price > prev_high and vol > avg_vol * 1.2:
        signals.append({'symbol': bars[i].get('symbol',''), 'direction': 'long', 'timeframe': bars[i].get('timeframe','1h'), 'entry': price, 'time': bars[i].get('ts')})
      elif price < prev_low and vol > avg_vol * 1.2:
        signals.append({'symbol': bars[i].get('symbol',''), 'direction': 'short', 'timeframe': bars[i].get('timeframe','1h'), 'entry': price, 'time': bars[i].get('ts')})
    return signals

class SMACross(Strategy):
  name = 'sma_cross'
  def generate(self, bars: List[Dict]) -> List[Dict]:
    closes = [b['close'] for b in bars]
    short = sma(closes, 10)
    long_ = sma(closes, 30)
    signals: List[Dict] = []
    for i in range(1, len(bars)):
      if i >= len(short) or i >= len(long_):
        break
      if short[i] is None or long_[i] is None or short[i-1] is None or long_[i-1] is None:
        continue
      if short[i] > long_[i] and short[i-1] <= long_[i-1]:
        signals.append({'symbol': bars[i].get('symbol',''), 'direction': 'long', 'timeframe': bars[i].get('timeframe','1h'), 'entry': closes[i], 'time': bars[i].get('ts')})
      elif short[i] < long_[i] and short[i-1] >= long_[i-1]:
        signals.append({'symbol': bars[i].get('symbol',''), 'direction': 'short', 'timeframe': bars[i].get('timeframe','1h'), 'entry': closes[i], 'time': bars[i].get('ts')})
    return signals

class CompositeStrategy:
  def __init__(self):
    self.strategies = [MomentumCross(), BreakoutPull(), SMACross()]
  def generate(self, bars: List[Dict]) -> List[Dict]:
    out: List[Dict] = []
    for s in self.strategies:
      try:
        sigs = s.generate(bars)
        out.extend(sigs)
      except Exception as e:
        import traceback
        print('strategy_fail', getattr(s, 'name', str(s)), repr(e))
        traceback.print_exc()
    return out

if __name__ == '__main__':
  import json, sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
  from TradeEngine.data import get_bars
  comp = CompositeStrategy()
  for sym in ['BTC/USD','ETH/USD','SOL/USD','EUR/USD','GBP/USD','USD/JPY']:
    try:
      bars = get_bars(sym)
      sigs = comp.generate(bars)
      print(sym, len(sigs))
      if sigs:
        print(json.dumps(sigs[-1], indent=2))
    except Exception as e:
      print(sym, 'ERROR', repr(e))
      import traceback
      traceback.print_exc()
