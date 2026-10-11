"""Тесты загрузки виртуальной файловой системы."""

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from vfs import VfsError, load_vfs, normalize  # noqa: E402

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
        self.assertEqual(load_vfs(MINIMAL_VFS).root.children, {})

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


if __name__ == "__main__":
    unittest.main()
