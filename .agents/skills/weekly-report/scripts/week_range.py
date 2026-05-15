#!/usr/bin/env python3
"""Print the current week's range.

Usage: week_range.py [monday|now|both]
- monday: ISO date of this week's Monday (default)
- now: ISO datetime of right now
- both: "<monday>\t<now>" tab separated
"""
import sys
from datetime import datetime, timedelta

now = datetime.now()
monday = (now - timedelta(days=now.weekday())).replace(
    hour=0, minute=0, second=0, microsecond=0
)

mode = sys.argv[1] if len(sys.argv) > 1 else "monday"
if mode == "monday":
    print(monday.date().isoformat())
elif mode == "now":
    print(now.isoformat(timespec="seconds"))
elif mode == "both":
    print(f"{monday.date().isoformat()}\t{now.isoformat(timespec='seconds')}")
else:
    sys.exit(f"unknown mode: {mode}")
