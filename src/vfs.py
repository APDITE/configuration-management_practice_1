"""Виртуальная файловая система (VFS), полностью хранящаяся в памяти.

Источник VFS — JSON-файл. Корень и каталоги описываются объектами
{"type": "dir", "children": {имя: узел, ...}}, файлы — объектами
{"type": "file", "content": "...", "encoding": "utf-8" | "base64"}.
Двоичные данные хранятся в кодировке base64.
"""

import base64
import binascii
import json

SEPARATOR = "/"
ROOT_PATH = "/"
TYPE_DIR = "dir"
TYPE_FILE = "file"
ENCODING_TEXT = "utf-8"
ENCODING_BASE64 = "base64"
RESERVED_NAMES = (".", "..")


class VfsError(Exception):
    """Ошибка загрузки VFS или обращения к её узлам."""


class VfsFile:
    """Файл VFS с содержимым в виде байтов."""

    is_dir = False

    def __init__(self, name, data=b""):
        """Создать файл с именем name и содержимым data."""
        self.name = name
        self.data = data

    def size(self):
        """Вернуть размер файла в байтах."""
        return len(self.data)


class VfsDir:
    """Каталог VFS, хранящий дочерние узлы по именам."""

    is_dir = True

    def __init__(self, name, children=None):
        """Создать каталог с именем name и словарём дочерних узлов."""
        self.name = name
        self.children = children if children is not None else {}

    def size(self):
        """Вернуть суммарный размер всех вложенных файлов в байтах."""
        return sum(child.size() for child in self.children.values())


def join_path(base, name):
    """Соединить путь каталога base и имя name."""
    return base.rstrip(SEPARATOR) + SEPARATOR + name


def normalize(path, cwd=ROOT_PATH):
    """Привести путь к абсолютному виду, раскрыв компоненты . и .."""
    if not path.startswith(SEPARATOR):
        path = join_path(cwd, path)
    parts = []
    for part in path.split(SEPARATOR):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return SEPARATOR + SEPARATOR.join(parts)


def check_name(name, where):
    """Проверить, что имя узла допустимо в файловой системе."""
    if not name or SEPARATOR in name or name in RESERVED_NAMES:
        raise VfsError(f"{where}: invalid name {name!r}")


def decode_content(content, encoding, where):
    """Преобразовать содержимое файла из JSON в байты."""
    if encoding == ENCODING_TEXT:
        return content.encode(ENCODING_TEXT)
    if encoding == ENCODING_BASE64:
        try:
            return base64.b64decode(content, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise VfsError(f"{where}: invalid base64 content") from exc
    raise VfsError(f"{where}: unknown encoding {encoding!r}")


def build_file(name, data, where):
    """Построить файл VFS из JSON-описания."""
    content = data.get("content", "")
    if not isinstance(content, str):
        raise VfsError(f"{where}: file content must be a string")
    encoding = data.get("encoding", ENCODING_TEXT)
    return VfsFile(name, decode_content(content, encoding, where))


def build_dir(name, data, where):
    """Построить каталог VFS со всеми вложенными узлами."""
    children = data.get("children", {})
    if not isinstance(children, dict):
        raise VfsError(f"{where}: 'children' must be an object")
    node = VfsDir(name)
    for child_name, child_data in children.items():
        check_name(child_name, where)
        child_where = join_path(where, child_name)
        node.children[child_name] = build_node(
            child_name, child_data, child_where
        )
    return node


def build_node(name, data, where):
    """Построить узел VFS (файл или каталог) из JSON-описания."""
    if not isinstance(data, dict):
        raise VfsError(f"{where}: node must be a JSON object")
    kind = data.get("type")
    if kind == TYPE_DIR:
        return build_dir(name, data, where)
    if kind == TYPE_FILE:
        return build_file(name, data, where)
    raise VfsError(f"{where}: unknown node type {kind!r}")


def load_vfs(path):
    """Загрузить VFS из JSON-файла в память и вернуть VirtualFS."""
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except OSError as exc:
        raise VfsError(f"cannot read '{path}': {exc.strerror}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise VfsError(f"invalid JSON in '{path}': {exc}") from exc
    root = build_node("", data, ROOT_PATH)
    if not root.is_dir:
        raise VfsError(f"{ROOT_PATH}: root must be a directory")
    return VirtualFS(root, source=path)


class VirtualFS:
    """Виртуальная файловая система с корневым каталогом root."""

    def __init__(self, root=None, source=None):
        """Создать VFS; без root создаётся пустой корневой каталог."""
        self.root = root if root is not None else VfsDir("")
        self.source = source

    def lookup(self, path, cwd=ROOT_PATH):
        """Найти узел по пути относительно cwd.

        Возвращает кортеж (абсолютный путь, узел).
        Бросает VfsError, если путь не существует.
        """
        abs_path = normalize(path, cwd)
        node = self.root
        for part in filter(None, abs_path.split(SEPARATOR)):
            if not node.is_dir:
                raise VfsError(f"{path}: Not a directory")
            if part not in node.children:
                raise VfsError(f"{path}: No such file or directory")
            node = node.children[part]
        return abs_path, node
