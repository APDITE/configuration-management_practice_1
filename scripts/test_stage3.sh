#!/bin/sh
# Проверка всех команд этапов 1-3 на VFS с глубокой вложенностью.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/src/emulator.py" \
    --vfs "$ROOT/vfs/deep.json" \
    --script "$ROOT/scripts/startup_stage3.txt"
echo "exit status: $?"
