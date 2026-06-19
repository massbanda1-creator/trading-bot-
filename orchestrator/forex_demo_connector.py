#!/usr/bin/env python3
"""
Minimal forex.com demo connector intent:

Assumptions based on available docs:
- Retail US FOREX.com REST API requires account setup + support activation before live use.
- Because of that, this module does not hardcode credentials.
- It exposes a demo_mode toggle and expects venue configuration from env or a small mapped config.

This gives TradeEngine a real seam to call without inventing secret credentials.
"""
from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

LOG = logging.getLogger("tradeengine.forex_demo")

DEMO_ACCOUNT_ID = os.environ.get("FOREX_DEMO_ACCOUNT", "demo-mass.banda1")
DEMO_ENV = os.environ.get("FOREX_DEMO_ENV", "demo")
DEFAULT_TIMEOUT_S = 20


@dataclass
class VenueConfig:
    account_id: str
    api_key: Optional[str] = None
    secret: Optional[str] = None
    token: Optional[str] = None
    base_url_env: str = "FOREX_DEMO_BASE_URL"
    timeout_s: int = DEFAULT_TIMEOUT_S
    headers: Dict[str, str] = field(default_factory=dict)

    @property
    def base_url(self) -> Optional[str]:
        return os.environ.get(self.base_url_env)

    @property
    def demo_default(self) -> bool:
        return (DEMO_ENV == "demo") and (not self.base_url)


@dataclass
class Bar:
    ts: float
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    symbol: str = ""
    timeframe: str = ""

    def __getitem__(self, key):
        mapping = {
            "ts": self.ts,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
        }
        if key not in mapping:
            raise KeyError(key)
        return mapping[key]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


def load_config() -> VenueConfig:
    return VenueConfig(
        account_id=DEMO_ACCOUNT_ID,
        api_key=os.environ.get("FOREX_API_KEY"),
        secret=os.environ.get("FOREX_API_SECRET"),
        token=os.environ.get("FOREX_API_TOKEN"),
    )


def require_config(cfg: VenueConfig) -> VenueConfig:
    if cfg.demo_default:
        return cfg
    missing = []
    if not cfg.account_id:
        missing.append("FOREX_DEMO_ACCOUNT")
    if not cfg.base_url:
        missing.append(f"{cfg.base_url_env}=https://...")
    if missing:
        raise RuntimeError(f"forex.com demo config missing: {', '.join(missing)}")
    return cfg


def log_config(cfg: VenueConfig) -> None:
    LOG.info(
        "connector configured for account=%s base_url=%s has_api_key=%s has_token=%s",
        cfg.account_id,
        cfg.base_url,
        bool(cfg.api_key),
        bool(cfg.token),
    )


# Example wireable interface names expected by the test loop:
def get_recent_bars(symbol: str, timeframe: str = "1h", limit: int = 200) -> List[Bar]:
    LOG.debug("forex_demo_connector.get_recent_bars: simulated demo bars for symbol=%s timeframe=%s limit=%s", symbol, timeframe, limit)
    return _simulate_bars(symbol, limit=limit)


def _simulate_bars(symbol: str, limit: int = 200) -> List[Bar]:
    import random
    random.seed(hash(symbol) % 2**32)
    base_prices = {
        "EUR/USD": 1.08,
        "GBP/USD": 1.27,
        "USD/JPY": 149.5,
        "AUD/USD": 0.66,
        "USD/CAD": 1.36,
    }
    base = base_prices.get(symbol, 1.0)
    now = time.time()
    bars: List[Bar] = []
    price = base
    # Add mixed trend signal patterns by simulating periodic up/down movements
    # Use sinusoidal trend + noise for realistic signals
    import math
    for i in range(limit):
        ts = now - (limit - i) * 3600
        open_ = price
        # Sinusoidal trend component to create up/down cycles
        trend = 0.0003 * price * math.sin(i / 25.0)
        noise = random.uniform(-0.0005, 0.0005) * price
        close = open_ + trend + noise
        high = max(open_, close) + abs(random.uniform(0, 0.0002 * price))
        low = min(open_, close) - abs(random.uniform(0, 0.0002 * price))
        bars.append(Bar(ts=ts, open=open_, high=high, low=low, close=close, volume=random.uniform(100, 1000), symbol=symbol, timeframe="1h"))
        price = close
    return bars


def place_order(symbol: str, side: str, quantity: float, order_type: str = "MARKET") -> Dict:
    LOG.info("forex_demo_connector.place_order: simulated order route=%s:%s symbol=%s side=%s qty=%s type=%s", DEMO_ENV, DEMO_ACCOUNT_ID, symbol, side, quantity, order_type)
    return {
        "status": "simulated_demo",
        "account": DEMO_ACCOUNT_ID,
        "environment": DEMO_ENV,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "order_type": order_type,
    }
