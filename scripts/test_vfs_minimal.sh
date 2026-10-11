#!/bin/sh
# Минимальная VFS: только пустой корневой каталог.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/src/emulator.py" \
    --vfs "$ROOT/vfs/minimal.json" \
    --script "$ROOT/scripts/startup_vfs_check.txt"
echo "exit status: $?"
