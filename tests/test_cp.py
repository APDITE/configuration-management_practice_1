"""Тесты команды cp: копирование файлов и каталогов VFS в памяти."""

import io
import os
import unittest

from shell import EXIT_ERROR, EXIT_OK, EXIT_USAGE, Shell
from vfs import load_vfs

ROOT = os.path.join(os.path.dirname(__file__), "..")
DEEP_VFS = os.path.join(ROOT, "vfs", "deep.json")


def make_shell():
    """Создать оболочку с VFS deep.json и перехваченным выводом."""
    return Shell(out=io.StringIO(), err=io.StringIO(),
                 vfs=load_vfs(DEEP_VFS))


def ls(shell, path):
    """Вернуть список имён в каталоге VFS."""
    _, node = shell.vfs.lookup(path, shell.cwd)
    return sorted(node.children)


class CpTest(unittest.TestCase):
    """Проверки успешного копирования."""

    def setUp(self):
        """Создать оболочку для каждого теста."""
        self.shell = make_shell()

    def test_file_new_name_and_into_dir(self):
        """Файл копируется под новым именем и внутрь каталога."""
        self.assertEqual(self.shell.execute("cp /etc/hosts /tmp/h"), EXIT_OK)
        self.shell.execute("cd /etc")
        self.shell.execute("cp passwd ../tmp")
        self.assertEqual(ls(self.shell, "/tmp"), ["h", "passwd"])
        self.assertEqual(ls(self.shell, "/etc"), ["hosts", "passwd"])

    def test_overwrite_file(self):
        """Существующий файл перезаписывается."""
        self.shell.execute("cp /etc/hosts /etc/passwd")
        _, node = self.shell.vfs.lookup("/etc/passwd")
        self.assertEqual(node.data, b"127.0.0.1 localhost\n")

    def test_directory_recursive(self):
        """Каталог копируется целиком с опцией -r."""
        self.shell.execute("cp -r /home/user/projects /tmp")
        _, node = self.shell.vfs.lookup("/tmp/projects/emulator/src/main.py")
        self.assertEqual(node.data, b"print('hello')\n")

    def test_several_sources(self):
        """Несколько источников копируются в каталог."""
        self.shell.execute("cp /etc/hosts /etc/passwd /var/log /tmp -r")
        self.assertEqual(ls(self.shell, "/tmp"), ["hosts", "log", "passwd"])

    def test_source_file_not_modified(self):
        """Изменения только в памяти: JSON-файл VFS не меняется."""
        with open(DEEP_VFS, "rb") as file:
            before = file.read()
        self.shell.execute("cp -r /home /tmp")
        with open(DEEP_VFS, "rb") as file:
            self.assertEqual(file.read(), before)


class CpErrorTest(unittest.TestCase):
    """Проверки ошибок команды cp."""

    def test_errors(self):
        """Каждая ошибка даёт сообщение и ненулевой код."""
        cases = {
            "cp": "cp: missing file operand",
            "cp /etc/hosts": "cp: missing destination file operand after "
                             "'/etc/hosts'",
            "cp /etc": "cp: missing destination file operand after '/etc'",
            "cp /etc /tmp": "cp: -r not specified; omitting directory "
                            "'/etc'",
            "cp -r /home /home/user": "cp: cannot copy a directory, "
                                      "'/home', into itself, '/home/user'",
            "cp /nope /tmp": "cp: /nope: No such file or directory",
            "cp /etc/hosts /no/x": "cp: cannot create '/no/x': No such "
                                   "file or directory",
            "cp /etc/hosts /etc/passwd /etc/hosts": "cp: target "
                                                    "'/etc/hosts' is not "
                                                    "a directory",
        }
        for line, message in cases.items():
            with self.subTest(line=line):
                shell = make_shell()
                self.assertEqual(shell.execute(line), EXIT_ERROR)
                self.assertEqual(shell.err.getvalue().strip(), message)

    def test_invalid_option(self):
        """Неизвестная опция."""
        shell = make_shell()
        self.assertEqual(shell.execute("cp -x a b"), EXIT_USAGE)
        self.assertIn("invalid option -- 'x'", shell.err.getvalue())


if __name__ == "__main__":
    unittest.main()
