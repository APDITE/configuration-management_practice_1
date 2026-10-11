"""Точка входа эмулятора командной оболочки UNIX-подобной ОС."""

from shell import Shell


def main():
    """Запустить эмулятор в интерактивном режиме."""
    Shell().repl()


if __name__ == "__main__":
    main()
