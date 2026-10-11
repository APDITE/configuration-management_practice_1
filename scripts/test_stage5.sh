#!/bin/sh
# Проверка команды cp (этап 5); после запуска JSON-файл VFS не меняется.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VFS="$ROOT/vfs/deep.json"
BEFORE="$(cksum < "$VFS")"
python3 "$ROOT/src/emulator.py" \
    --vfs "$VFS" \
    --script "$ROOT/scripts/startup_stage5.txt"
echo "exit status: $?"
if [ "$(cksum < "$VFS")" = "$BEFORE" ]; then
    echo "vfs/deep.json не изменён"
else
    echo "ОШИБКА: vfs/deep.json изменён"
    exit 1
fi
