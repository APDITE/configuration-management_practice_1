#!/bin/sh
# Запуск эмулятора без параметров: параметры не заданы.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
printf 'conf-dump\nexit\n' | python3 "$ROOT/src/emulator.py"
echo "exit status: $?"
