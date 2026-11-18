#!/bin/sh
cd "$(dirname "$0")" || exit 1
export PYTHONUTF8=1
if command -v python3 >/dev/null 2>&1; then
  python3 run.py --open
else
  python run.py --open
fi
