#!/usr/bin/env python3
"""
Local-only trade plan generator.
Reads verified cache from TradeEngine/data.py through cache_read()/get_bars().
Outputs plan.json with simple SMA-based conditions.
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/Users/banda/Desktop/TradeEngine')
from data import cache_read, get_bars  # use verified source

OUT = Path('/Users/banda/Desktop/TradeEngine/data/plan.json')

def sma(values, window):
  if not values or len(values) < window:
    return None
  return sum(values[-window:]) / window

def generate_plan():
  cache = cache_read()
  SYMBOLS = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD', 'XRP/USD']
  plan = {
    'generated_at': datetime.now().isoformat(),
    'mode': 'sma_local_only',
    'rules': {'short_window': 5, 'long_window': 20},
    'ideas': [],
  }
  for sym in SYMBOLS:
    bars = get_bars(sym)
    close = bars[-1]['close'] if bars else None
    closes = [b['close'] for b in bars]
    short = sma(closes, 5)
    long_ = sma(closes, 20)
    if close is None or short is None or long_ is None:
      idea = {
        'symbol': sym,
        'latest_close': None,
        'signal': 'neutral',
        'confidence': 'low',
        'note': 'insufficient cached bars',
      }
    else:
      idea = {
        'symbol': sym,
        'latest_close': close,
        'signal': 'long' if close > short else 'contracting',
        'confidence': 'medium',
        'last_bars': len(closes),
      }
    plan['ideas'].append(idea)
  OUT.write_text(__import__('json').dumps(plan, indent=2))
  print('plan_written', OUT)
if __name__ == '__main__':
  generate_plan()
