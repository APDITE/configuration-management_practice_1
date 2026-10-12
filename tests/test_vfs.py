"""Тесты виртуальной файловой системы и служебных команд VFS."""

import io
import json
import os
import tempfile
import unittest

from config import Config
from emulator import run
from shell import EXIT_ERROR, Shell
from vfs import VfsError, count_nodes, load_vfs, normalize

ROOT = os.path.join(os.path.dirname(__file__), "..")
DEEP_VFS = os.path.join(ROOT, "vfs", "deep.json")
SEVERAL_VFS = os.path.join(ROOT, "vfs", "several_files.json")
MINIMAL_VFS = os.path.join(ROOT, "vfs", "minimal.json")
PNG_SIGNATURE = b"\x89PNG"


def write_json(test, text):
    """Записать текст во временный JSON-файл и вернуть путь к нему."""
    file = tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    )
    with file:
        file.write(text)
    test.addCleanup(os.remove, file.name)
    return file.name


def make_shell(vfs_path=DEEP_VFS):
    """Создать оболочку с загруженной VFS и перехваченным выводом."""
    return Shell(out=io.StringIO(), err=io.StringIO(),
                 vfs=load_vfs(vfs_path))


class NormalizeTest(unittest.TestCase):
    """Проверки нормализации путей."""

    def test_absolute(self):
        """Абсолютный путь не зависит от текущего каталога."""
        self.assertEqual(normalize("/etc/./hosts", "/home"), "/etc/hosts")

    def test_relative_and_parent(self):
        """Относительный путь и .. раскрываются от текущего каталога."""
        self.assertEqual(normalize("../etc", "/home/user"), "/home/etc")

    def test_above_root(self):
        """Выход выше корня остаётся в корне."""
        self.assertEqual(normalize("../../..", "/home"), "/")


class LoadVfsTest(unittest.TestCase):
    """Проверки загрузки VFS из JSON."""

    def test_minimal(self):
        """Минимальная VFS содержит только пустой корень."""
        self.assertEqual(count_nodes(load_vfs(MINIMAL_VFS).root), (0, 0))

    def test_base64_file(self):
        """Двоичный файл декодируется из base64."""
        _, node = load_vfs(SEVERAL_VFS).lookup("/logo.png")
        self.assertTrue(node.data.startswith(PNG_SIGNATURE))

    def test_deep_lookup(self):
        """Поиск узла на глубине нескольких уровней."""
        path, node = load_vfs(DEEP_VFS).lookup(
            "src/main.py", "/home/user/projects/emulator"
        )
        self.assertEqual(path, "/home/user/projects/emulator/src/main.py")
        self.assertEqual(node.data, b"print('hello')\n")

    def test_lookup_errors(self):
        """Несуществующий путь и файл вместо каталога дают ошибку."""
        vfs = load_vfs(DEEP_VFS)
        with self.assertRaisesRegex(VfsError, "No such file"):
            vfs.lookup("/nope")
        with self.assertRaisesRegex(VfsError, "Not a directory"):
            vfs.lookup("/etc/hosts/x")

    def test_invalid_sources(self):
        """Ошибки источника: нет файла, неверный JSON, неверная структура."""
        cases = [
            "/no/such/file.json",
            write_json(self, "{broken"),
            write_json(self, '{"type": "file"}'),
            write_json(self, '{"type": "dir", "children": {"a": 1}}'),
            write_json(self, json.dumps({"type": "dir", "children": {
                "x": {"type": "file", "encoding": "base64",
                      "content": "!!"}}})),
            write_json(self, '{"type": "dir", "children": {"..": '
                             '{"type": "dir"}}}'),
        ]
        for path in cases:
            with self.subTest(path=path), self.assertRaises(VfsError):
                load_vfs(path)

    def test_source_not_modified(self):
        """Загрузка VFS не изменяет исходный файл."""
        before = os.path.getmtime(DEEP_VFS)
        make_shell().execute("vfs-tree /")
        self.assertEqual(os.path.getmtime(DEEP_VFS), before)


class VfsCommandsTest(unittest.TestCase):
    """Проверки служебных команд vfs-info и vfs-tree."""

    def test_prompt_uses_vfs_cwd(self):
        """Приглашение показывает текущий каталог VFS."""
        self.assertTrue(make_shell().prompt().endswith(":/$ "))

    def test_vfs_info(self):
        """vfs-info выводит число каталогов и файлов."""
        shell = make_shell(SEVERAL_VFS)
        shell.execute("vfs-info")
        self.assertIn("directories=0\nfiles=4\n", shell.out.getvalue())

    def test_vfs_tree(self):
        """vfs-tree выводит вложенные узлы с отступами."""
        shell = make_shell()
        shell.execute("vfs-tree /home/user/projects")
        self.assertEqual(shell.out.getvalue().splitlines(), [
            "/home/user/projects",
            "└── emulator/",
            "    ├── README.md",
            "    └── src/",
            "        └── main.py",
        ])

    def test_vfs_tree_errors(self):
        """vfs-tree сообщает об ошибках пути и аргументов."""
        shell = make_shell()
        self.assertEqual(shell.execute("vfs-tree /nope"), EXIT_ERROR)
        self.assertEqual(shell.execute("vfs-tree / /etc"), EXIT_ERROR)
        self.assertIn("No such file", shell.err.getvalue())

    def test_bad_vfs_stops_emulator(self):
        """Ошибка загрузки VFS завершает эмулятор с кодом 1."""
        config = Config(vfs_path=write_json(self, "[]"))
        shell = Shell(config, out=io.StringIO(), err=io.StringIO())
        self.assertEqual(run(config, shell), EXIT_ERROR)
        self.assertIn("vfs: /: node must be", shell.err.getvalue())


class CopyTest(unittest.TestCase):
    """Проверки копирования узлов VFS в памяти."""

    def setUp(self):
        """Загрузить VFS с глубокой вложенностью."""
        self.vfs = load_vfs(DEEP_VFS)

    def test_copy_file(self):
        """Файл копируется под новым именем и внутрь каталога."""
        self.assertEqual(self.vfs.copy("/etc/hosts", "/tmp/h"), "/tmp/h")
        self.assertEqual(self.vfs.copy("hosts", "/tmp", "/etc"),
                         "/tmp/hosts")
        _, node = self.vfs.lookup("/tmp/h")
        self.assertEqual(node.data, b"127.0.0.1 localhost\n")

    def test_copy_dir_is_deep(self):
        """Копия каталога независима от оригинала."""
        self.vfs.copy("/home/user/docs", "/tmp/docs", recursive=True)
        self.vfs.copy("/etc/hosts", "/tmp/docs")
        _, original = self.vfs.lookup("/home/user/docs")
        self.assertNotIn("hosts", original.children)
        _, copy = self.vfs.lookup("/tmp/docs/photo.png")
        self.assertEqual(copy.data, original.children["photo.png"].data)

    def test_copy_dir_merges(self):
        """Каталог объединяется с одноимённым, ничего не теряется."""
        self.vfs.copy("/home/user/docs", "/tmp", recursive=True)
        self.vfs.copy("/etc/hosts", "/tmp/docs")
        self.vfs.copy("/home/user/docs", "/tmp", recursive=True)
        _, node = self.vfs.lookup("/tmp/docs")
        self.assertEqual(sorted(node.children),
                         ["hosts", "photo.png", "report.txt"])

    def test_lookup_file_with_slash(self):
        """Путь к файлу с / в конце — ошибка Not a directory."""
        with self.assertRaisesRegex(VfsError, "Not a directory"):
            self.vfs.lookup("/etc/hosts/")

    def test_errors(self):
        """Ошибки копирования."""
        cases = [
            ("/home", "/tmp", False, "-r not specified"),
            ("/home", "/home/user", True, "into itself"),
            ("/", "/tmp", True, "into itself"),
            ("/nope", "/tmp", False, "No such file"),
            ("/etc/hosts", "/no/dir/x", False, "cannot create"),
            ("/etc/hosts", "/etc/hosts", False, "same file"),
            ("/var", "/etc/hosts", True, "cannot overwrite non-directory"),
            ("/etc/hosts", "/etc/hosts/", False, "Not a directory"),
            ("/tmp", "/tmp", True, "into itself, '/tmp/tmp'"),
        ]
        for src, dst, recursive, message in cases:
            with self.subTest(src=src, dst=dst):
                with self.assertRaisesRegex(VfsError, message):
                    self.vfs.copy(src, dst, recursive=recursive)


if __name__ == "__main__":
    unittest.main()
