"""Ядро эмулятора: приглашение к вводу, парсер, команды и скрипты."""

import getpass
import socket
import sys
from datetime import datetime

from config import Config
from vfs import ROOT_PATH, VfsError, VirtualFS, count_nodes, disk_usage
from vfs import render_tree

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2
EXIT_NOT_FOUND = 127
COMMENT = "#"
OPTION_PREFIX = "-"
CURRENT_DIR = "."
SIZE_WIDTH = 8
DATE_FORMAT = "%a %b %d %H:%M:%S %Z %Y"
FORMAT_PREFIX = "+"


class ShellExit(Exception):
    """Сигнал о завершении работы эмулятора командой exit."""


def make_prompt(cwd):
    """Сформировать приглашение вида username@hostname:cwd$.

    Имя пользователя и хоста берутся из ОС, cwd — текущий каталог VFS.
    """
    user = getpass.getuser()
    host = socket.gethostname().split(".")[0]
    return f"{user}@{host}:{cwd}$ "


def parse(line):
    """Разделить строку ввода на команду и аргументы по пробелам.

    Слово, начинающееся с #, и всё после него — комментарий
    (как в Python и sh); # внутри слова сохраняется.
    Для пустой строки возвращает (None, []).
    """
    parts = []
    for word in line.split():
        if word.startswith(COMMENT):
            break
        parts.append(word)
    if not parts:
        return None, []
    return parts[0], parts[1:]


def local_now():
    """Вернуть текущие дату и время ОС с локальным часовым поясом."""
    return datetime.now().astimezone()


def split_options(args):
    """Отделить короткие опции (-a, -la) от остальных аргументов.

    Возвращает кортеж (множество букв опций, список аргументов).
    """
    options, operands = set(), []
    for arg in args:
        if arg.startswith(OPTION_PREFIX) and arg != OPTION_PREFIX:
            options.update(arg[1:])
        else:
            operands.append(arg)
    return options, operands


def visible_entries(node, show_hidden):
    """Вернуть отсортированные пары (имя, узел) содержимого каталога.

    Имена, начинающиеся с точки, скрыты, если show_hidden ложно.
    """
    return [
        (name, node.children[name]) for name in sorted(node.children)
        if show_hidden or not name.startswith(".")
    ]


def format_entry(name, node, long_format):
    """Отформатировать одну запись вывода ls."""
    if not long_format:
        return name
    kind = "d" if node.is_dir else "-"
    return f"{kind} {node.size():>{SIZE_WIDTH}} {name}"


class Shell:
    """Эмулятор командной оболочки UNIX-подобной ОС."""

    def __init__(self, config=None, out=None, err=None, vfs=None):
        """Создать оболочку с настройками config и файловой системой vfs.

        Результаты выводятся в поток out, ошибки — в поток err.
        Без vfs используется пустая VFS в памяти.
        """
        self.config = config or Config()
        self.vfs = vfs or VirtualFS()
        self.cwd = ROOT_PATH
        self.clock = local_now
        self.out = out or sys.stdout
        self.err = err or sys.stderr
        self.commands = {
            "ls": self.cmd_ls,
            "cd": self.cmd_cd,
            "du": self.cmd_du,
            "date": self.cmd_date,
            "cp": self.cmd_cp,
            "exit": self.cmd_exit,
            "conf-dump": self.cmd_conf_dump,
            "vfs-info": self.cmd_vfs_info,
            "vfs-tree": self.cmd_vfs_tree,
        }

    def prompt(self):
        """Вернуть приглашение к вводу с текущим каталогом VFS."""
        return make_prompt(self.cwd)

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
        """Запустить интерактивный цикл: приглашение, ввод, выполнение.

        Ctrl+D завершает работу, Ctrl+C сбрасывает текущую строку.
        """
        while True:
            try:
                line = input(self.prompt())
            except EOFError:
                self.print()
                return
            except KeyboardInterrupt:
                self.print()
                continue
            try:
                self.execute(line)
            except ShellExit:
                return

    def print_debug_config(self):
        """Отладочный вывод всех параметров эмулятора при запуске."""
        for key, value in self.config.items():
            self.error(f"[debug] {key} = {value or '(not set)'}")

    def run_script(self, path):
        """Выполнить стартовый скрипт, имитируя диалог с пользователем.

        Пустые строки и строки-комментарии пропускаются. Об ошибке
        сообщается с номером строки, выполнение продолжается.
        Возвращает False, если скрипт не удалось прочитать.
        При вызове exit бросает ShellExit.
        """
        try:
            with open(path, encoding="utf-8") as file:
                lines = file.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            reason = getattr(exc, "strerror", None) or exc
            self.error(f"script: cannot read '{path}': {reason}")
            return False
        for number, line in enumerate(lines, start=1):
            if parse(line)[0] is None:
                continue
            self.print(self.prompt() + line)
            status = self.execute(line)
            if status != EXIT_OK:
                self.error(
                    f"script error: {path}:{number}: exit status {status}"
                )
        return True

    def check_options(self, command, options, allowed):
        """Проверить опции команды; сообщить о первой недопустимой."""
        for option in sorted(options - set(allowed)):
            self.error(f"{command}: invalid option -- '{option}'")
            return False
        return True

    def cmd_ls(self, args):
        """Вывести содержимое каталогов VFS: ls [-a] [-l] [путь...].

        -a — показывать скрытые файлы, -l — тип и размер в байтах.
        """
        options, paths = split_options(args)
        if not self.check_options("ls", options, "al"):
            return EXIT_USAGE
        paths = paths or [CURRENT_DIR]
        status = EXIT_OK
        for index, path in enumerate(paths):
            try:
                _, node = self.vfs.lookup(path, self.cwd)
            except VfsError as exc:
                self.error(f"ls: cannot access {exc}")
                status = EXIT_ERROR
                continue
            if paths[1:] and node.is_dir:
                self.print(("\n" if index else "") + f"{path}:")
            self.print_listing(path, node, options)
        return status

    def print_listing(self, path, node, options):
        """Вывести список файлов каталога или имя файла для ls."""
        long_format = "l" in options
        if node.is_dir:
            entries = visible_entries(node, "a" in options)
        else:
            entries = [(path, node)]
        lines = [format_entry(n, e, long_format) for n, e in entries]
        if long_format:
            for line in lines:
                self.print(line)
        elif lines:
            self.print("  ".join(lines))

    def cmd_cd(self, args):
        """Сменить текущий каталог VFS: cd [путь].

        Без аргумента переходит в корневой каталог.
        """
        if args[1:]:
            self.error("cd: too many arguments")
            return EXIT_ERROR
        target = args[0] if args else ROOT_PATH
        try:
            path, node = self.vfs.lookup(target, self.cwd)
        except VfsError as exc:
            self.error(f"cd: {exc}")
            return EXIT_ERROR
        if not node.is_dir:
            self.error(f"cd: {target}: Not a directory")
            return EXIT_ERROR
        self.cwd = path
        return EXIT_OK

    def cmd_du(self, args):
        """Вывести размеры в байтах: du [-a] [-s] [путь...].

        По умолчанию выводятся все вложенные каталоги, -a добавляет
        файлы, -s оставляет только итог для каждого пути.
        """
        options, paths = split_options(args)
        if not self.check_options("du", options, "as"):
            return EXIT_USAGE
        if {"a", "s"} <= options:
            self.error("du: cannot both summarize and show all entries")
            return EXIT_USAGE
        status = EXIT_OK
        for path in paths or [CURRENT_DIR]:
            try:
                _, node = self.vfs.lookup(path, self.cwd)
            except VfsError as exc:
                self.error(f"du: cannot access {exc}")
                status = EXIT_ERROR
                continue
            if "s" in options:
                usage = [(node.size(), path)]
            else:
                usage = disk_usage(node, path, "a" in options)
            for size, name in usage:
                self.print(f"{size}\t{name}")
        return status

    def cmd_date(self, args):
        """Вывести текущие дату и время ОС: date [+ФОРМАТ].

        Формат задаётся как в strftime, например date +%Y-%m-%d.
        """
        if args[1:]:
            self.error(f"date: extra operand '{args[1]}'")
            return EXIT_ERROR
        date_format = DATE_FORMAT
        if args:
            if not args[0].startswith(FORMAT_PREFIX):
                self.error(f"date: invalid date '{args[0]}'")
                return EXIT_ERROR
            date_format = args[0][len(FORMAT_PREFIX):]
        self.print(self.clock().strftime(date_format))
        return EXIT_OK

    def is_dir(self, path):
        """Проверить, что путь существует и является каталогом VFS."""
        try:
            _, node = self.vfs.lookup(path, self.cwd)
        except VfsError:
            return False
        return node.is_dir

    def cmd_cp(self, args):
        """Копировать в памяти: cp [-r] ИСТОЧНИК... НАЗНАЧЕНИЕ.

        Каталоги копируются только с опцией -r (или -R). При нескольких
        источниках назначение должно быть каталогом.
        """
        options, paths = split_options(args)
        if not self.check_options("cp", options, "rR"):
            return EXIT_USAGE
        if not paths:
            self.error("cp: missing file operand")
            return EXIT_ERROR
        if not paths[1:]:
            self.error(
                f"cp: missing destination file operand after '{paths[0]}'"
            )
            return EXIT_ERROR
        *sources, dest = paths
        if sources[1:] and not self.is_dir(dest):
            self.error(f"cp: target '{dest}' is not a directory")
            return EXIT_ERROR
        recursive = bool(options & set("rR"))
        status = EXIT_OK
        for src in sources:
            try:
                self.vfs.copy(src, dest, self.cwd, recursive)
            except VfsError as exc:
                self.error(f"cp: {exc}")
                status = EXIT_ERROR
        return status

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

    def cmd_vfs_info(self, args):
        """Служебная: вывести источник и статистику загруженной VFS."""
        if args:
            self.error("vfs-info: too many arguments")
            return EXIT_ERROR
        dirs, files = count_nodes(self.vfs.root)
        self.print(f"source={self.vfs.source or '(empty in-memory VFS)'}")
        self.print(f"directories={dirs}")
        self.print(f"files={files}")
        self.print(f"size={self.vfs.root.size()}")
        return EXIT_OK

    def cmd_vfs_tree(self, args):
        """Служебная: вывести дерево VFS начиная с пути (по умолчанию .)."""
        if args[1:]:
            self.error("vfs-tree: too many arguments")
            return EXIT_ERROR
        try:
            path, node = self.vfs.lookup(args[0] if args else ".", self.cwd)
        except VfsError as exc:
            self.error(f"vfs-tree: {exc}")
            return EXIT_ERROR
        self.print(path)
        if node.is_dir:
            for line in render_tree(node):
                self.print(line)
        return EXIT_OK
