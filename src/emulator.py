"""Точка входа эмулятора командной оболочки UNIX-подобной ОС."""

import sys

from config import parse_args
from shell import EXIT_OK, Shell


def run(config, shell):
    """Вывести параметры и запустить REPL.

    Возвращает код завершения эмулятора.
    """
    shell.print_debug_config()
    shell.repl()
    return EXIT_OK


def main(argv=None):
    """Разобрать параметры и запустить эмулятор."""
    config = parse_args(argv)
    return run(config, Shell(config))


if __name__ == "__main__":
    sys.exit(main())
