"""Тесты конфигурации: параметры, conf-dump и стартовый скрипт."""

import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import Config, parse_args  # noqa: E402
from emulator import run  # noqa: E402
from shell import EXIT_ERROR, EXIT_OK, Shell  # noqa: E402


def make_shell(config=None):
    """Создать оболочку с перехваченными потоками вывода."""
    return Shell(config, out=io.StringIO(), err=io.StringIO())


def write_script(test, text):
    """Записать текст во временный файл скрипта и вернуть путь к нему.

    Файл удаляется после завершения теста test.
    """
    file = tempfile.NamedTemporaryFile(
        "w", suffix=".txt", delete=False, encoding="utf-8"
    )
    with file:
        file.write(text)
    test.addCleanup(os.remove, file.name)
    return file.name


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


class ScriptTest(unittest.TestCase):
    """Проверки выполнения стартового скрипта."""

    def test_comments_and_echo(self):
        """Комментарии пропускаются, команды отображаются с приглашением."""
        path = write_script(self, "# comment\n\nls a  # tail\n")
        shell = make_shell()
        self.assertTrue(shell.run_script(path))
        lines = shell.out.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].endswith("$ ls a  # tail"))
        self.assertEqual(lines[1], "ls: args = ['a']")

    def test_reports_error_and_continues(self):
        """Об ошибке сообщается с номером строки, скрипт продолжается."""
        path = write_script(self, "ls\nbad\nls next\n")
        shell = make_shell()
        self.assertTrue(shell.run_script(path))
        self.assertIn(f"{path}:2: exit status 127", shell.err.getvalue())
        self.assertIn("ls: args = ['next']", shell.out.getvalue())

    def test_missing_script(self):
        """Отсутствующий скрипт приводит к ошибке."""
        shell = make_shell()
        self.assertFalse(shell.run_script("/no/such.txt"))

    def test_missing_script_exit_code(self):
        """Эмулятор завершается с кодом 1, если скрипт не найден."""
        config = Config(script_path="/no/such.txt")
        self.assertEqual(run(config, make_shell(config)), EXIT_ERROR)

    def test_exit_in_script(self):
        """exit в скрипте завершает эмулятор, остальные строки пропускаются."""
        config = Config(script_path=write_script(self, "exit\nls\n"))
        shell = make_shell(config)
        self.assertEqual(run(config, shell), EXIT_OK)
        self.assertNotIn("ls: args", shell.out.getvalue())


if __name__ == "__main__":
    unittest.main()
