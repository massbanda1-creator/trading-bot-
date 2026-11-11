#!/usr/bin/env python3
"""Looping wrapper for forex demo trade runs."""
from __future__ import annotations

import json
import subprocess
import sys
import time

ROOT = "/Users/banda/Desktop/trading-bot-flat"
SCRIPT = f"{ROOT}/orchestrator/run_forex_demo.py"
INTERVAL_SECONDS = 60 * 5  # every 5 minutes

def run_cycle() -> None:
    proc = subprocess.run(
        [sys.executable, SCRIPT],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    if proc.returncode != 0:
        print(f"[{time.strftime('%H:%M:%S')}] cycle failed rc={proc.returncode}")
        if stderr:
            print(stderr[-800:])
        return
    print(f"[{time.strftime('%H:%M:%S')}] cycle ok")
    if stdout:
        try:
            data = json.loads(stdout)
            print(f"  orders_placed={data.get('orders_placed',0)} account_realized_pips={data.get('account_realized_pips',0)}")
        except Exception:
            print(stdout[-600:])

def main() -> None:
    print(f"Starting forex demo loop every {INTERVAL_SECONDS}s...")
    while True:
        try:
            run_cycle()
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] loop error: {e}")
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
