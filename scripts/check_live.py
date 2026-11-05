"""Optional network smoke check: python scripts/check_live.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hitrade.data import get_history


if __name__ == "__main__":
    frame = get_history("RELIANCE.NS", "Yahoo Finance")
    print(f"RELIANCE.NS: {len(frame)} validated candles; latest {frame.index[-1]:%Y-%m-%d}")
