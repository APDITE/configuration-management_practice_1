"""Параметры эмулятора, задаваемые в командной строке."""

import argparse
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Настройки эмулятора."""

    vfs_path: str = None
    script_path: str = None

    def items(self):
        """Вернуть параметры в виде списка пар (ключ, значение)."""
        return [
            ("vfs", absolute_or_empty(self.vfs_path)),
            ("script", absolute_or_empty(self.script_path)),
        ]


def absolute_or_empty(path):
    """Вернуть абсолютный путь или пустую строку, если путь не задан."""
    return os.path.abspath(path) if path else ""


def build_parser():
    """Создать парсер аргументов командной строки эмулятора."""
    parser = argparse.ArgumentParser(
        prog="emulator",
        description="Эмулятор командной оболочки UNIX-подобной ОС.",
    )
    parser.add_argument(
        "--vfs", dest="vfs_path", metavar="PATH",
        help="путь к физическому расположению VFS (JSON-файл)",
    )
    parser.add_argument(
        "--script", dest="script_path", metavar="PATH",
        help="путь к стартовому скрипту эмулятора",
    )
    return parser


def parse_args(argv=None):
    """Разобрать аргументы командной строки и вернуть Config."""
    args = build_parser().parse_args(argv)
    return Config(vfs_path=args.vfs_path, script_path=args.script_path)
