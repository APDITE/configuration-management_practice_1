"""Тесты этапа 1: приглашение, парсер, заглушки и exit."""

import contextlib
import getpass
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from shell import make_prompt, parse, run_command  # noqa: E402


def run_and_capture(name, args):
    """Выполнить команду и вернуть (результат, выведенный текст)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        result = run_command(name, args)
    return result, out.getvalue()


class PromptTest(unittest.TestCase):
    """Проверки приглашения к вводу."""

    def test_prompt_format(self):
        """Приглашение имеет вид username@hostname:каталог$."""
        prompt = make_prompt()
        self.assertTrue(prompt.startswith(getpass.getuser() + "@"))
        self.assertTrue(prompt.endswith("$ "))


class ParseTest(unittest.TestCase):
    """Проверки разбора строки на команду и аргументы."""

    def test_split_by_spaces(self):
        """Команда и аргументы разделяются пробелами."""
        self.assertEqual(parse("ls  -l   /home"), ("ls", ["-l", "/home"]))

    def test_empty_line(self):
        """Пустая строка даёт пустую команду."""
        self.assertEqual(parse("   "), (None, []))


class CommandTest(unittest.TestCase):
    """Проверки команд-заглушек и exit."""

    def test_stubs(self):
        """ls и cd выводят своё имя и аргументы."""
        self.assertEqual(run_and_capture("ls", ["-a", "dir"]),
                         (True, "ls: args = ['-a', 'dir']\n"))
        self.assertEqual(run_and_capture("cd", []),
                         (True, "cd: args = []\n"))

    def test_unknown_command(self):
        """Неизвестная команда сообщает об ошибке."""
        self.assertEqual(run_and_capture("foo", []),
                         (True, "foo: command not found\n"))

    def test_exit(self):
        """exit завершает работу."""
        self.assertEqual(run_and_capture("exit", []), (False, ""))

    def test_exit_with_args(self):
        """exit с аргументами сообщает об ошибке и не завершает работу."""
        self.assertEqual(run_and_capture("exit", ["1"]),
                         (True, "exit: too many arguments\n"))


if __name__ == "__main__":
    unittest.main()
