#!/usr/bin/env python3
"""
Market data module for TradeEngine.
Sources: CoinGecko public REST for crypto, forex currently requires keyed provider.
"""
import json, os, time, datetime, pathlib
import urllib.request

CACHE = pathlib.Path('/Users/banda/Desktop/TradeEngine/data/market_cache.json')
DATA_DIR = pathlib.Path('/Users/banda/Desktop/TradeEngine/data')
DATA_DIR.mkdir(parents=True, exist_ok=True)

SYMBOL_MAP = {
  'BTC/USD': 'bitcoin',
  'ETH/USD': 'ethereum',
  'SOL/USD': 'solana',
  'BNB/USD': 'binancecoin',
  'XRP/USD': 'ripple',
}

def cache_write(obj):
  CACHE.write_text(json.dumps({'ts': time.time(), 'data': obj}, indent=2))

def cache_read() -> dict:
  if not CACHE.exists():
    return {}
  try:
    raw = json.loads(CACHE.read_text())
    return raw.get('data', {})
  except Exception:
    return {}

def fetch_coingecko(coin_id: str, days='1', interval='hourly') -> list[dict]:
  url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval={interval}'
  req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
  try:
    with urllib.request.urlopen(req, timeout=20) as r:
      raw = json.load(r)
  except Exception as e:
    print('coingecko_fetch_fail', coin_id, repr(e))
    return []
  prices = raw.get('prices', [])
  volumes = raw.get('total_volumes', [])
  out = []
  for i, (ts_ms, price) in enumerate(prices):
    vol = volumes[i][1] if i < len(volumes) else 0.0
    out.append({
      'ts': ts_ms / 1000,
      'open': price,
      'high': price,
      'low': price,
      'close': price,
      'volume': vol,
      'symbol': next((k for k,v in SYMBOL_MAP.items() if v == coin_id), coin_id),
      'timeframe': '1h',
    })
  return out

CACHE_TTL = 15 * 60  # 15 minutes per symbol cache

def cache_key(symbol: str):
  return f'{symbol.replace("/", "_")}_{int(time.time() // CACHE_TTL)}'

def get_bars(symbol: str, timeframe='1h', limit=200) -> list[dict]:
  coin_id = SYMBOL_MAP.get(symbol)
  if not coin_id:
    return []
  key = cache_key(symbol)
  cached = cache_read().get(symbol)
  if cached and isinstance(cached, dict) and cached.get('key') == key:
    return cached.get('bars', [])[-limit:]
  days = '1' if timeframe in ('1h', '15m') else '7'
  interval = 'hourly' if timeframe in ('1h', '15m') else 'hourly'
  bars = fetch_coingecko(coin_id, days=days, interval=interval)
  cache = cache_read()
  cache[symbol] = {'key': key, 'bars': bars}
  cache_write(cache)
  return bars[-limit:]

def latest(symbol: str):
  bars = get_bars(symbol)
  return bars[-1] if bars else {}

if __name__ == '__main__':
  print(json.dumps({sym: {'latest': latest(sym)} for sym in SYMBOL_MAP}, indent=2))
