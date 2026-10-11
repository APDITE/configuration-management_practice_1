"""Тесты REPL: приглашение, парсер, заглушки и команда exit."""

import getpass
import io
import unittest

from shell import EXIT_ERROR, EXIT_NOT_FOUND, Shell, ShellExit
from shell import make_prompt, parse


def make_shell():
    """Создать оболочку с перехваченными потоками вывода."""
    return Shell(out=io.StringIO(), err=io.StringIO())


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

    def test_stub_prints_args(self):
        """Заглушка выводит имя команды и аргументы."""
        shell = make_shell()
        shell.execute("ls -a dir")
        self.assertEqual(shell.out.getvalue(), "ls: args = ['-a', 'dir']\n")

    def test_unknown_command(self):
        """Неизвестная команда сообщает об ошибке."""
        shell = make_shell()
        self.assertEqual(shell.execute("foo"), EXIT_NOT_FOUND)
        self.assertIn("foo: command not found", shell.err.getvalue())

    def test_exit(self):
        """exit завершает работу."""
        with self.assertRaises(ShellExit):
            make_shell().execute("exit")

    def test_exit_with_args(self):
        """exit с аргументами сообщает об ошибке и не завершает работу."""
        shell = make_shell()
        self.assertEqual(shell.execute("exit 1"), EXIT_ERROR)
        self.assertIn("exit: too many arguments", shell.err.getvalue())


if __name__ == "__main__":
    unittest.main()
