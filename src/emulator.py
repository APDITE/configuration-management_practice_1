"""Точка входа эмулятора командной оболочки UNIX-подобной ОС."""

import sys

from config import parse_args
from shell import EXIT_ERROR, EXIT_OK, Shell, ShellExit
from vfs import VfsError, load_vfs


def load_configured_vfs(config, shell):
    """Загрузить VFS, указанную в параметрах, в оболочку shell.

    Возвращает False, если VFS загрузить не удалось.
    """
    if not config.vfs_path:
        return True
    try:
        shell.vfs = load_vfs(config.vfs_path)
    except VfsError as exc:
        shell.error(f"vfs: {exc}")
        return False
    return True


def run(config, shell):
    """Загрузить VFS, выполнить стартовый скрипт и запустить REPL.

    Возвращает код завершения эмулятора.
    """
    shell.print_debug_config()
    if not load_configured_vfs(config, shell):
        return EXIT_ERROR
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
