"""Тесты основных команд: cd, ls, du и date."""

import io
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from shell import EXIT_ERROR, EXIT_OK, EXIT_USAGE, Shell  # noqa: E402
from vfs import load_vfs  # noqa: E402

DEEP_VFS = os.path.join(ROOT, "vfs", "deep.json")
MSK = timezone(timedelta(hours=3), "MSK")
FIXED_NOW = datetime(2026, 10, 11, 17, 5, 9, tzinfo=MSK)


def make_shell():
    """Создать оболочку с VFS deep.json и перехваченным выводом."""
    return Shell(out=io.StringIO(), err=io.StringIO(),
                 vfs=load_vfs(DEEP_VFS))


def run(shell, line):
    """Выполнить команду и вернуть (код, вывод, ошибки), очистив потоки."""
    status = shell.execute(line)
    out, err = shell.out.getvalue(), shell.err.getvalue()
    shell.out.seek(0)
    shell.out.truncate()
    shell.err.seek(0)
    shell.err.truncate()
    return status, out, err


class CdTest(unittest.TestCase):
    """Проверки команды cd."""

    def test_absolute_and_relative(self):
        """cd меняет текущий каталог и приглашение."""
        shell = make_shell()
        self.assertEqual(run(shell, "cd /home/user")[0], EXIT_OK)
        self.assertEqual(shell.cwd, "/home/user")
        run(shell, "cd docs")
        self.assertEqual(shell.cwd, "/home/user/docs")
        run(shell, "cd ../..")
        self.assertEqual(shell.cwd, "/home")
        self.assertTrue(shell.prompt().endswith(":/home$ "))

    def test_no_args_goes_to_root(self):
        """cd без аргументов переходит в корень."""
        shell = make_shell()
        run(shell, "cd /etc")
        run(shell, "cd")
        self.assertEqual(shell.cwd, "/")

    def test_errors(self):
        """Ошибки cd не меняют текущий каталог."""
        shell = make_shell()
        cases = {
            "cd /nope": "cd: /nope: No such file or directory",
            "cd /etc/hosts": "cd: /etc/hosts: Not a directory",
            "cd /etc /var": "cd: too many arguments",
        }
        for line, message in cases.items():
            with self.subTest(line=line):
                status, _, err = run(shell, line)
                self.assertEqual(status, EXIT_ERROR)
                self.assertEqual(err.strip(), message)
                self.assertEqual(shell.cwd, "/")


class LsTest(unittest.TestCase):
    """Проверки команды ls."""

    def test_current_dir(self):
        """ls без аргументов выводит содержимое текущего каталога."""
        shell = make_shell()
        run(shell, "cd /home/user")
        self.assertEqual(run(shell, "ls"), (EXIT_OK, "docs  projects\n", ""))

    def test_hidden_and_long(self):
        """-a показывает скрытые файлы, -l выводит тип и размер."""
        shell = make_shell()
        _, out, _ = run(shell, "ls -a /home/user")
        self.assertEqual(out, ".bashrc  docs  projects\n")
        _, out, _ = run(shell, "ls -l /etc")
        self.assertEqual(out.splitlines(), [
            "-       20 hosts",
            "-       67 passwd",
        ])

    def test_file_and_several_paths(self):
        """Для файла выводится его имя, для нескольких путей — заголовки."""
        shell = make_shell()
        self.assertEqual(run(shell, "ls /etc/hosts")[1], "/etc/hosts\n")
        _, out, _ = run(shell, "ls /etc /var")
        self.assertEqual(out, "/etc:\nhosts  passwd\n\n/var:\nlog\n")

    def test_errors(self):
        """Ошибки: несуществующий путь и неизвестная опция."""
        shell = make_shell()
        status, _, err = run(shell, "ls /nope /etc")
        self.assertEqual(status, EXIT_ERROR)
        self.assertIn("ls: cannot access /nope: No such file", err)
        status, _, err = run(shell, "ls -z")
        self.assertEqual(status, EXIT_USAGE)
        self.assertEqual(err, "ls: invalid option -- 'z'\n")


class DuTest(unittest.TestCase):
    """Проверки команды du."""

    def test_directories(self):
        """du выводит размеры вложенных каталогов, затем итог."""
        _, out, _ = run(make_shell(), "du /home/user/projects")
        self.assertEqual(out.splitlines(), [
            "15\t/home/user/projects/emulator/src",
            "26\t/home/user/projects/emulator",
            "26\t/home/user/projects",
        ])

    def test_summary_and_files(self):
        """-s выводит только итог, -a добавляет файлы."""
        shell = make_shell()
        self.assertEqual(run(shell, "du -s /")[1], "324\t/\n")
        _, out, _ = run(shell, "du -a /etc")
        self.assertEqual(out.splitlines(), [
            "20\t/etc/hosts", "67\t/etc/passwd", "87\t/etc",
        ])

    def test_relative_and_file(self):
        """Относительный путь и путь к файлу."""
        shell = make_shell()
        run(shell, "cd /var")
        self.assertEqual(run(shell, "du log/syslog")[1], "34\tlog/syslog\n")
        self.assertEqual(run(shell, "du")[1], "34\t./log\n34\t.\n")

    def test_errors(self):
        """Ошибки: несуществующий путь и неизвестная опция."""
        shell = make_shell()
        status, _, err = run(shell, "du /nope")
        self.assertEqual(status, EXIT_ERROR)
        self.assertIn("du: cannot access /nope", err)
        self.assertEqual(run(shell, "du -x")[0], EXIT_USAGE)
        status, _, err = run(shell, "du -as /etc")
        self.assertEqual(status, EXIT_USAGE)
        self.assertIn("cannot both summarize and show all entries", err)
        status, _, err = run(shell, "du /etc/hosts/")
        self.assertEqual(status, EXIT_ERROR)
        self.assertIn("/etc/hosts/: Not a directory", err)


class DateTest(unittest.TestCase):
    """Проверки команды date с подменёнными часами."""

    def setUp(self):
        """Создать оболочку с фиксированным текущим временем."""
        self.shell = make_shell()
        self.shell.clock = lambda: FIXED_NOW

    def test_default_format(self):
        """Без аргументов дата выводится как в UNIX."""
        self.assertEqual(run(self.shell, "date"),
                         (EXIT_OK, "Sun Oct 11 17:05:09 MSK 2026\n", ""))

    def test_custom_format(self):
        """+ФОРМАТ задаёт формат вывода."""
        self.assertEqual(run(self.shell, "date +%Y-%m-%d")[1],
                         "2026-10-11\n")

    def test_real_clock(self):
        """По умолчанию используется время ОС."""
        _, out, _ = run(make_shell(), "date +%Y")
        self.assertEqual(out.strip(), str(datetime.now().year))

    def test_errors(self):
        """Ошибки: аргумент без + и лишний аргумент."""
        self.assertEqual(run(self.shell, "date tomorrow")[2],
                         "date: invalid date 'tomorrow'\n")
        self.assertEqual(run(self.shell, "date +%Y +%m")[0], EXIT_ERROR)


if __name__ == "__main__":
    unittest.main()
