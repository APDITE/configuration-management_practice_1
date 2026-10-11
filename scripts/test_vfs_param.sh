#!/bin/sh
# Запуск эмулятора только с параметром --vfs.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
printf 'conf-dump\nexit\n' \
    | python3 "$ROOT/src/emulator.py" --vfs "$ROOT/vfs/minimal.json"
echo "exit status: $?"
