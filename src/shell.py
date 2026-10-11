"""Ядро эмулятора: приглашение к вводу, парсер и команды."""

import getpass
import os
import socket


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


def run_command(name, args):
    """Выполнить команду. Вернуть False, если нужно завершить работу."""
    if name in ("ls", "cd"):
        print(f"{name}: args = {args}")
        return True
    if name == "exit":
        if args:
            print("exit: too many arguments")
            return True
        return False
    print(f"{name}: command not found")
    return True


def repl():
    """Запустить интерактивный цикл: приглашение, ввод, выполнение."""
    while True:
        try:
            line = input(make_prompt())
        except (EOFError, KeyboardInterrupt):
            print()
            return
        name, args = parse(line)
        if name is not None and not run_command(name, args):
            return
