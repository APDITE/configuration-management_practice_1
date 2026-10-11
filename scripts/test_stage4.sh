#!/bin/sh
# Проверка команд этапа 4 (ls, cd, du, date) на VFS с глубокой вложенностью.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/src/emulator.py" \
    --vfs "$ROOT/vfs/deep.json" \
    --script "$ROOT/scripts/startup_stage4.txt"
echo "exit status: $?"
