"""Тесты REPL: приглашение, парсер и базовые команды."""

import getpass
import io
import unittest
from unittest import mock

from shell import EXIT_ERROR, EXIT_NOT_FOUND, Shell, ShellExit
from shell import make_prompt, parse


def make_shell():
    """Создать оболочку с перехваченными потоками вывода."""
    return Shell(out=io.StringIO(), err=io.StringIO())


class PromptTest(unittest.TestCase):
    """Проверки приглашения к вводу."""

    def test_prompt_format(self):
        """Приглашение имеет вид username@hostname:каталог_VFS$."""
        prompt = make_prompt("/home")
        self.assertTrue(prompt.startswith(getpass.getuser() + "@"))
        self.assertTrue(prompt.endswith(":/home$ "))


class ParseTest(unittest.TestCase):
    """Проверки разбора строки на команду и аргументы."""

    def test_split_by_spaces(self):
        """Команда и аргументы разделяются пробелами."""
        self.assertEqual(parse("ls  -l   /home"), ("ls", ["-l", "/home"]))

    def test_empty_line(self):
        """Пустая строка даёт пустую команду."""
        self.assertEqual(parse("   "), (None, []))

    def test_comment(self):
        """Всё после # отбрасывается."""
        self.assertEqual(parse("ls a # b c"), ("ls", ["a"]))
        self.assertEqual(parse("# only comment"), (None, []))
        self.assertEqual(parse("ls file#1 #c"), ("ls", ["file#1"]))


class CommandTest(unittest.TestCase):
    """Проверки команд ls и exit в пустой VFS."""

    def test_ls_empty_vfs(self):
        """ls в пустой VFS ничего не выводит."""
        shell = make_shell()
        self.assertEqual(shell.execute("ls"), 0)
        self.assertEqual(shell.out.getvalue(), "")

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


class ReplTest(unittest.TestCase):
    """Проверки интерактивного цикла с подменённым вводом."""

    def test_ctrl_c_keeps_running(self):
        """Ctrl+C сбрасывает строку, работа продолжается до exit."""
        shell = make_shell()
        lines = iter([KeyboardInterrupt(), "foo", "exit", "never"])

        def fake_input(_prompt):
            """Вернуть очередную строку или бросить исключение."""
            item = next(lines)
            if isinstance(item, BaseException):
                raise item
            return item

        with mock.patch("builtins.input", fake_input):
            shell.repl()
        self.assertIn("foo: command not found", shell.err.getvalue())
        self.assertEqual(next(lines), "never")

    def test_ctrl_d_exits(self):
        """Ctrl+D (конец ввода) завершает работу."""
        shell = make_shell()
        with mock.patch("builtins.input", side_effect=EOFError):
            shell.repl()
        self.assertEqual(shell.out.getvalue(), "\n")


if __name__ == "__main__":
    unittest.main()
