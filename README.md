# Эмулятор командной оболочки UNIX (вариант 17)

Практическая работа № 1 по дисциплине «Конфигурационное управление».

## Общее описание

Консольное приложение (CLI) на Python 3, имитирующее работу в командной
строке UNIX-подобной ОС. Приглашение к вводу строится по реальным данным
ОС: `имя_пользователя@имя_хоста:каталог$`.

Сторонние зависимости не требуются — только стандартная библиотека
Python 3.8+.

## Структура репозитория

```
src/
  emulator.py   точка входа
  config.py     параметры командной строки
  shell.py      приглашение, парсер, команды, REPL, стартовый скрипт
scripts/        стартовые скрипты эмулятора (*.txt) и скрипты ОС (*.sh)
tests/          модульные тесты (unittest)
run.sh          запуск эмулятора и тестов
```

## Настройки

Параметры командной строки:

| Параметр | Описание |
|---|---|
| `--vfs PATH` | путь к физическому расположению VFS |
| `--script PATH` | путь к стартовому скрипту эмулятора |
| `-h`, `--help` | справка по параметрам |

При запуске все параметры выводятся в отладочном виде (в stderr):

```
[debug] vfs = /path/to/vfs.json
[debug] script = (not set)
```

### Стартовый скрипт

Текстовый файл, каждая строка которого — команда эмулятора.
Комментарии начинаются с `#` (синтаксис Python), пустые строки
пропускаются. Каждая команда выводится вместе с приглашением, а затем
её результат — так имитируется диалог с пользователем.

Если команда завершилась ошибкой, выводится сообщение с номером строки,
и выполнение продолжается:

```
script error: scripts/startup_error.txt:4: exit status 127
```

Если скрипт не содержит `exit`, после него эмулятор переходит
в интерактивный режим. Команда `exit` в скрипте завершает эмулятор.

## Функции

| Функция / команда | Описание |
|---|---|
| приглашение | `user@host:~$` — имя пользователя, имя хоста и текущий каталог ОС |
| парсер | делит строку на команду и аргументы по пробелам; всё после `#` — комментарий |
| `ls [арг...]` | заглушка: выводит имя команды и аргументы |
| `cd [арг...]` | заглушка: выводит имя команды и аргументы |
| `exit` | завершает работу эмулятора |
| `conf-dump` | служебная: выводит параметры эмулятора в формате `ключ=значение` |

### Обработка ошибок

| Ситуация | Сообщение |
|---|---|
| неизвестная команда | `foo: command not found` |
| `exit` / `conf-dump` с аргументами | `exit: too many arguments` (работа продолжается) |
| стартовый скрипт не найден | `script: cannot read '...': No such file or directory` (выход с кодом 1) |
| неизвестный параметр запуска | `emulator: error: unrecognized arguments: ...` (выход с кодом 2) |

Пустая строка игнорируется. `Ctrl+D` / `Ctrl+C` завершают работу.

## Сборка и запуск

Сборка не требуется.

```sh
./run.sh                                   # интерактивный режим
./run.sh --script scripts/startup_basic.txt
./run.sh test                              # запуск тестов
```

Скрипты ОС для проверки параметров командной строки:

```sh
scripts/test_no_params.sh      # без параметров
scripts/test_vfs_param.sh      # только --vfs
scripts/test_script_param.sh   # только --script
scripts/test_all_params.sh     # оба параметра
scripts/test_errors.sh         # ошибки запуска и стартового скрипта
```

Без `run.sh`:

```sh
python3 src/emulator.py
python3 -m unittest discover -s tests -v
```

## Примеры использования

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

Запуск со стартовым скриптом:

```
$ ./run.sh --script scripts/startup_basic.txt
[debug] vfs = (not set)
[debug] script = /home/user/practice/scripts/startup_basic.txt
user@host:~/practice$ conf-dump
vfs=
script=/home/user/practice/scripts/startup_basic.txt
user@host:~/practice$ ls -l /home       # комментарий в конце строки отбрасывается
ls: args = ['-l', '/home']
user@host:~/practice$ cd /tmp
cd: args = ['/tmp']
user@host:~/practice$ ls
ls: args = []
user@host:~/practice$ exit
```
