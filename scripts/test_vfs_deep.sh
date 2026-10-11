#!/bin/sh
# VFS с вложенностью файлов и каталогов не менее 3 уровней.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/src/emulator.py" \
    --vfs "$ROOT/vfs/deep.json" \
    --script "$ROOT/scripts/startup_vfs_check.txt"
echo "exit status: $?"
