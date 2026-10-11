#!/bin/sh
# Запуск эмулятора: ./run.sh [параметры]
# Запуск тестов:    ./run.sh test
DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$1" = "test" ]; then
    cd "$DIR" && exec python3 -m unittest discover -s tests -v
fi

exec python3 "$DIR/src/emulator.py" "$@"
