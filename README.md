# Эмулятор оболочки UNIX (вариант 17)

Консольный эмулятор командной строки UNIX на Python 3.
Приглашение строится по реальным данным ОС.

## Структура

```
src/
  emulator.py   точка входа
  shell.py      приглашение, парсер, команды, REPL
tests/          тесты (unittest)
run.sh          запуск эмулятора и тестов
```

## Команды

- `ls`, `cd` — заглушки, выводят имя и аргументы
- `exit` — выход

## Запуск

```sh
./run.sh          # запуск эмулятора
./run.sh test     # запуск тестов
```

Без `run.sh`:

```sh
python3 src/emulator.py
python3 -m unittest discover -s tests -t . -v
```

## Пример

```
user@host:~/practice$ ls -l /home
ls: args = ['-l', '/home']
user@host:~/practice$ cd /tmp
cd: args = ['/tmp']
user@host:~/practice$
user@host:~/practice$ foo bar
foo: command not found
user@host:~/practice$ exit 1
exit: too many arguments
user@host:~/practice$ exit
```
