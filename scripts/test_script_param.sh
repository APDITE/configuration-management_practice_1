#!/bin/sh
# Запуск эмулятора только с параметром --script.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/src/emulator.py" \
    --script "$ROOT/scripts/startup_basic.txt" < /dev/null
echo "exit status: $?"
