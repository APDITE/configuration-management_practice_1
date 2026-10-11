#!/bin/sh
# Ошибки: сбой в стартовом скрипте, отсутствующий скрипт,
# неизвестный параметр командной строки.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "--- error inside startup script ---"
python3 "$ROOT/src/emulator.py" \
    --script "$ROOT/scripts/startup_error.txt" < /dev/null
echo "exit status: $?"

echo "--- missing startup script ---"
python3 "$ROOT/src/emulator.py" --script "$ROOT/no/such/file.txt" < /dev/null
echo "exit status: $?"

echo "--- unknown option ---"
python3 "$ROOT/src/emulator.py" --unknown < /dev/null
echo "exit status: $?"
