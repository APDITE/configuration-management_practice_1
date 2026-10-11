"""Ядро эмулятора: приглашение к вводу, парсер и команды."""

import getpass
import os
import socket
import sys

from config import Config

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_NOT_FOUND = 127


class ShellExit(Exception):
    """Сигнал о завершении работы эмулятора командой exit."""


def make_prompt():
    """Сформировать приглашение вида username@hostname:~$ по данным ОС."""
    user = getpass.getuser()
    host = socket.gethostname().split(".")[0]
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd == home or cwd.startswith(home + os.sep):
        cwd = "~" + cwd[len(home):]
    return f"{user}@{host}:{cwd}$ "


def parse(line):
    """Разделить строку ввода на команду и аргументы по пробелам.

    Для пустой строки возвращает (None, []).
    """
    parts = line.split()
    if not parts:
        return None, []
    return parts[0], parts[1:]


class Shell:
    """Эмулятор командной оболочки UNIX-подобной ОС."""

    def __init__(self, config=None, out=None, err=None):
        """Создать оболочку с настройками config.

        Результаты выводятся в поток out, ошибки — в поток err.
        """
        self.config = config or Config()
        self.out = out or sys.stdout
        self.err = err or sys.stderr
        self.commands = {
            "ls": self.cmd_ls,
            "cd": self.cmd_cd,
            "exit": self.cmd_exit,
            "conf-dump": self.cmd_conf_dump,
        }

    def prompt(self):
        """Вернуть приглашение к вводу."""
        return make_prompt()

    def print(self, text=""):
        """Вывести строку в поток вывода оболочки."""
        print(text, file=self.out, flush=True)

    def error(self, text):
        """Вывести сообщение об ошибке в поток ошибок оболочки."""
        print(text, file=self.err, flush=True)

    def execute(self, line):
        """Выполнить одну строку ввода и вернуть код возврата.

        При вызове exit бросает ShellExit.
        """
        name, args = parse(line)
        if name is None:
            return EXIT_OK
        handler = self.commands.get(name)
        if handler is None:
            self.error(f"{name}: command not found")
            return EXIT_NOT_FOUND
        return handler(args)

    def repl(self):
        """Запустить интерактивный цикл: приглашение, ввод, выполнение."""
        while True:
            try:
                line = input(self.prompt())
            except (EOFError, KeyboardInterrupt):
                self.print()
                return
            try:
                self.execute(line)
            except ShellExit:
                return

    def print_debug_config(self):
        """Отладочный вывод всех параметров эмулятора при запуске."""
        for key, value in self.config.items():
            self.error(f"[debug] {key} = {value or '(not set)'}")

    def stub(self, name, args):
        """Заглушка: вывести имя команды и её аргументы."""
        self.print(f"{name}: args = {args}")
        return EXIT_OK

    def cmd_ls(self, args):
        """Команда ls (заглушка)."""
        return self.stub("ls", args)

    def cmd_cd(self, args):
        """Команда cd (заглушка)."""
        return self.stub("cd", args)

    def cmd_exit(self, args):
        """Завершить работу эмулятора."""
        if args:
            self.error("exit: too many arguments")
            return EXIT_ERROR
        raise ShellExit()

    def cmd_conf_dump(self, args):
        """Вывести параметры эмулятора в формате ключ=значение."""
        if args:
            self.error("conf-dump: too many arguments")
            return EXIT_ERROR
        for key, value in self.config.items():
            self.print(f"{key}={value}")
        return EXIT_OK
