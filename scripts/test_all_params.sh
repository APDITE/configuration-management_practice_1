#!/bin/sh
# Запуск эмулятора со всеми параметрами командной строки.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/src/emulator.py" \
    --vfs "$ROOT/vfs/minimal.json" \
    --script "$ROOT/scripts/startup_basic.txt" < /dev/null
echo "exit status: $?"
