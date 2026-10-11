#!/bin/sh
# VFS из нескольких файлов, включая двоичный (base64).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/src/emulator.py" \
    --vfs "$ROOT/vfs/several_files.json" \
    --script "$ROOT/scripts/startup_vfs_check.txt"
echo "exit status: $?"
