"""Точка входа эмулятора командной оболочки UNIX-подобной ОС."""

import sys

from config import parse_args
from shell import EXIT_ERROR, EXIT_OK, Shell, ShellExit


def run(config, shell):
    """Выполнить стартовый скрипт (если задан) и запустить REPL.

    Возвращает код завершения эмулятора.
    """
    shell.print_debug_config()
    try:
        if config.script_path and not shell.run_script(config.script_path):
            return EXIT_ERROR
        shell.repl()
    except ShellExit:
        pass
    return EXIT_OK


def main(argv=None):
    """Разобрать параметры и запустить эмулятор."""
    config = parse_args(argv)
    return run(config, Shell(config))


if __name__ == "__main__":
    sys.exit(main())
