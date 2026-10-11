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

TREE_BRANCH = "├── "
TREE_LAST = "└── "
TREE_PIPE = "│   "
TREE_SPACE = "    "


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


def split_path(abs_path):
    """Разделить абсолютный путь на (путь родителя, имя)."""
    parent, _, name = abs_path.rpartition(SEPARATOR)
    return parent or ROOT_PATH, name


def clone(node, name):
    """Вернуть глубокую копию узла node под именем name."""
    if not node.is_dir:
        return VfsFile(name, node.data)
    children = {
        child_name: clone(child, child_name)
        for child_name, child in node.children.items()
    }
    return VfsDir(name, children)


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


def render_tree(node, prefix=""):
    """Вернуть строки дерева для дочерних узлов каталога node."""
    lines = []
    names = sorted(node.children)
    for index, name in enumerate(names):
        child = node.children[name]
        last = index == len(names) - 1
        suffix = SEPARATOR if child.is_dir else ""
        lines.append(prefix + (TREE_LAST if last else TREE_BRANCH)
                     + name + suffix)
        if child.is_dir:
            extension = TREE_SPACE if last else TREE_PIPE
            lines.extend(render_tree(child, prefix + extension))
    return lines


def count_nodes(node):
    """Подсчитать число каталогов и файлов внутри каталога node."""
    dirs, files = 0, 0
    for child in node.children.values():
        if child.is_dir:
            sub_dirs, sub_files = count_nodes(child)
            dirs += 1 + sub_dirs
            files += sub_files
        else:
            files += 1
    return dirs, files


def disk_usage(node, path, include_files=False):
    """Вернуть список (размер, путь) для каталога и всех вложенных.

    Порядок как у du: сначала вложенные каталоги, затем сам каталог.
    С include_files в список попадают и файлы.
    """
    if not node.is_dir:
        return [(node.size(), path)]
    usage = []
    for name in sorted(node.children):
        child = node.children[name]
        if child.is_dir or include_files:
            usage.extend(
                disk_usage(child, join_path(path, name), include_files)
            )
    usage.append((node.size(), path))
    return usage


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

    def copy_target(self, dst, cwd, src_name):
        """Определить, куда копировать: (каталог, путь каталога, имя).

        Если dst — существующий каталог, копия кладётся внутрь него
        под именем src_name, иначе dst задаёт новое имя копии.
        """
        dst_path = normalize(dst, cwd)
        try:
            _, node = self.lookup(dst_path)
        except VfsError:
            node = None
        if node is not None and node.is_dir:
            return node, dst_path, src_name
        parent_path, name = split_path(dst_path)
        try:
            _, parent = self.lookup(parent_path)
        except VfsError:
            parent = None
        if parent is None or not parent.is_dir:
            raise VfsError(
                f"cannot create '{dst}': No such file or directory"
            )
        return parent, parent_path, name

    def copy(self, src, dst, cwd=ROOT_PATH, recursive=False):
        """Скопировать узел src в dst в памяти; вернуть путь копии.

        Каталог копируется только при recursive. Исходный JSON-файл
        VFS не изменяется. Ошибки сообщаются через VfsError.
        """
        src_path, node = self.lookup(src, cwd)
        if node.is_dir and not recursive:
            raise VfsError(f"-r not specified; omitting directory '{src}'")
        parent, parent_path, name = self.copy_target(dst, cwd, node.name)
        target = join_path(parent_path, name)
        inside = (target + SEPARATOR).startswith(
            src_path.rstrip(SEPARATOR) + SEPARATOR
        )
        if node.is_dir and inside:
            raise VfsError(
                f"cannot copy a directory, '{src}', into itself, '{dst}'"
            )
        existing = parent.children.get(name)
        if existing is node:
            raise VfsError(f"'{src}' and '{dst}' are the same file")
        if existing is not None and existing.is_dir != node.is_dir:
            raise VfsError(f"cannot overwrite '{target}': type mismatch")
        parent.children[name] = clone(node, name)
        return target
