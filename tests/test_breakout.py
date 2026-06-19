#!/usr/bin/env python3
import sys, json
from pathlib import Path
sys.path.insert(0, '/Users/banda/Desktop/TradeEngine')
from strategy import BreakoutPull

def make_bars_with_breakout():
  bars = []
  # Build 25 bars where close trends up then breaks previous 20-bar high on last bar
  base = 100.0
  for i in range(25):
    bar = {
      'ts': 1000000 + i*3600,
      'open': base,
      'high': base + 1.5,
      'low': base - 1.0,
      'close': base,
      'volume': 1000.0,
      'symbol': 'TEST/USD',
      'timeframe': '1h',
    }
    bars.append(bar)
    base += 0.5
  # Last bar breaks previous high by 2.0 and has higher volume
  bars[-1]['close'] = bars[-1]['high'] = bars[-1]['open'] = base + 3.0
  bars[-1]['volume'] = 2500.0
  return bars

bars = make_bars_with_breakout()
strat = BreakoutPull()
sigs = strat.generate(bars)
print('breakout_test', len(sigs))
if sigs:
  print(json.dumps(sigs[0], indent=2))
else:
  print('no_signals')
