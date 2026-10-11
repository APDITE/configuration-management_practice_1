#!/bin/sh
# Ошибки загрузки VFS: файл не найден, неверный JSON, неверная структура.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for vfs in no_such_file.json invalid/broken.json invalid/bad_type.json \
           invalid/bad_base64.json invalid/root_is_file.json; do
    echo "--- $vfs ---"
    python3 "$ROOT/src/emulator.py" --vfs "$ROOT/vfs/$vfs" < /dev/null
    echo "exit status: $?"
done
