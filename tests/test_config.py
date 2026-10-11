"""Тесты конфигурации: параметры, отладочный вывод и conf-dump."""

import io
import unittest

from config import Config, parse_args
from shell import EXIT_ERROR, Shell


def make_shell(config=None):
    """Создать оболочку с перехваченными потоками вывода."""
    return Shell(config, out=io.StringIO(), err=io.StringIO())


class ParseArgsTest(unittest.TestCase):
    """Проверки разбора параметров командной строки."""

    def test_defaults(self):
        """Без параметров пути не заданы."""
        self.assertEqual(parse_args([]), Config())

    def test_all_params(self):
        """Оба параметра сохраняются в конфигурации."""
        config = parse_args(["--vfs", "a.json", "--script", "s.txt"])
        self.assertEqual(config.vfs_path, "a.json")
        self.assertEqual(config.script_path, "s.txt")


class ConfDumpTest(unittest.TestCase):
    """Проверки служебной команды conf-dump."""

    def test_dump_key_value(self):
        """conf-dump выводит параметры в формате ключ=значение."""
        shell = make_shell(Config(vfs_path="/tmp/v.json"))
        shell.execute("conf-dump")
        self.assertEqual(shell.out.getvalue(), "vfs=/tmp/v.json\nscript=\n")

    def test_dump_extra_args(self):
        """conf-dump не принимает аргументов."""
        self.assertEqual(make_shell().execute("conf-dump x"), EXIT_ERROR)

    def test_debug_output(self):
        """При запуске выводятся все параметры."""
        shell = make_shell(Config(script_path="/tmp/s.txt"))
        shell.print_debug_config()
        self.assertIn("[debug] script = /tmp/s.txt", shell.err.getvalue())
        self.assertIn("[debug] vfs = (not set)", shell.err.getvalue())


if __name__ == "__main__":
    unittest.main()
