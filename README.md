# Эмулятор командной оболочки UNIX (вариант 17)

Практическая работа № 1 по дисциплине «Конфигурационное управление».

## Общее описание

Консольное приложение (CLI) на Python 3, имитирующее работу в командной
строке UNIX-подобной ОС. Эмулятор работает с виртуальной файловой
системой (VFS), которая загружается из JSON-файла и полностью хранится
в памяти: исходный файл никогда не изменяется.

Приглашение к вводу строится по реальным данным ОС (имя пользователя и
имя хоста) и текущему каталогу VFS: `user@host:/home/user$`.

Сторонние зависимости не требуются — только стандартная библиотека
Python 3.8+.

## Структура репозитория

```
src/
  emulator.py   точка входа: параметры, загрузка VFS, скрипт, REPL
  config.py     параметры командной строки
  shell.py      приглашение, парсер, диспетчер команд, REPL, скрипты
  vfs.py        виртуальная файловая система в памяти
vfs/            примеры VFS (vfs/invalid/ — заведомо ошибочные)
scripts/        стартовые скрипты эмулятора (*.txt) и скрипты ОС (*.sh)
tests/          модульные тесты (unittest)
run.sh          запуск эмулятора и тестов
```

## Настройки

Параметры командной строки:

| Параметр | Описание |
|---|---|
| `--vfs PATH` | путь к JSON-файлу VFS; без параметра используется пустая VFS |
| `--script PATH` | путь к стартовому скрипту эмулятора |
| `-h`, `--help` | справка по параметрам |

При запуске все параметры выводятся в отладочном виде (в stderr):

```
[debug] vfs = /path/to/vfs.json
[debug] script = (not set)
```

### Формат VFS

Корень и каталоги — объекты с типом `dir` и словарём `children`
(имя → узел). Файлы — объекты с типом `file` и полем `content`.
Двоичные данные хранятся в base64 (`"encoding": "base64"`), текст —
как есть (`"encoding": "utf-8"`, значение по умолчанию).

```json
{
  "type": "dir",
  "children": {
    "etc": {
      "type": "dir",
      "children": {
        "hosts": {"type": "file", "content": "127.0.0.1 localhost\n"}
      }
    },
    "logo.png": {"type": "file", "encoding": "base64", "content": "iVBORw0K..."}
  }
}
```

Примеры в каталоге `vfs/`:

| Файл | Содержимое |
|---|---|
| `minimal.json` | только пустой корневой каталог |
| `several_files.json` | несколько файлов в корне, включая двоичный PNG |
| `deep.json` | дерево каталогов глубиной до 6 уровней |
| `invalid/*.json` | ошибки: битый JSON, неизвестный тип узла, неверный base64, файл в корне |

При ошибке загрузки VFS эмулятор сообщает причину и завершается с
кодом 1.

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
| приглашение | `user@host:/cwd$` — имя пользователя и хоста ОС, текущий каталог VFS |
| парсер | делит строку на команду и аргументы по пробелам; всё после `#` — комментарий |
| `ls [-a] [-l] [путь...]` | содержимое каталогов (по умолчанию — текущего); `-a` — со скрытыми файлами, `-l` — тип (`d`/`-`) и размер в байтах |
| `cd [путь]` | сменить текущий каталог VFS; без аргумента — переход в корень `/` |
| `du [-a] [-s] [путь...]` | размер в байтах каждого вложенного каталога и итог; `-a` — и файлов, `-s` — только итог |
| `date [+ФОРМАТ]` | текущие дата и время ОС; формат как в `strftime`, например `date +%Y-%m-%d` |
| `exit` | завершает работу эмулятора |
| `conf-dump` | служебная: выводит параметры эмулятора в формате `ключ=значение` |
| `vfs-info` | служебная: источник VFS, число каталогов и файлов, общий размер |
| `vfs-tree [путь]` | служебная: дерево VFS от указанного пути (по умолчанию — текущий каталог); поддерживаются абсолютные и относительные пути, `.` и `..` |

### Обработка ошибок

| Ситуация | Сообщение | Код |
|---|---|---|
| неизвестная команда | `foo: command not found` | 127 |
| лишние аргументы | `exit: too many arguments`, `cd: too many arguments` (работа продолжается) | 1 |
| неизвестная опция | `ls: invalid option -- 'z'` | 2 |
| путь для `ls`/`du` не существует | `ls: cannot access /nope: No such file or directory` | 1 |
| `cd` в несуществующий каталог или файл | `cd: /nope: No such file or directory`, `cd: /etc/hosts: Not a directory` | 1 |
| неверный аргумент `date` | `date: invalid date 'tomorrow'`, `date: extra operand '+%m'` | 1 |
| путь не существует | `vfs-tree: /nope: No such file or directory` | 1 |
| файл вместо каталога | `vfs-tree: /etc/hosts/x: Not a directory` | 1 |
| стартовый скрипт не найден | `script: cannot read '...': No such file or directory` | 1 (выход) |
| VFS не найдена / неверна | `vfs: cannot read '...'`, `vfs: invalid JSON in '...'`, `vfs: /a.txt: unknown node type 'link'` | 1 (выход) |
| неизвестный параметр запуска | `emulator: error: unrecognized arguments: ...` | 2 (выход) |

Пустая строка игнорируется. `Ctrl+D` / `Ctrl+C` завершают работу.

## Сборка и запуск

Сборка не требуется.

```sh
./run.sh                                  # интерактивный режим, пустая VFS
./run.sh --vfs vfs/deep.json              # интерактивный режим с VFS
./run.sh --vfs vfs/deep.json --script scripts/startup_stage3.txt
./run.sh test                             # запуск тестов
```

Без `run.sh`:

```sh
python3 src/emulator.py --vfs vfs/deep.json
python3 -m unittest discover -s tests -t . -v
```

Скрипты ОС (`scripts/*.sh`):

| Скрипт | Что проверяет |
|---|---|
| `test_no_params.sh` | запуск без параметров |
| `test_vfs_param.sh` | только `--vfs` |
| `test_script_param.sh` | только `--script` |
| `test_all_params.sh` | оба параметра |
| `test_errors.sh` | ошибки в стартовом скрипте, отсутствующий скрипт, неизвестный параметр |
| `test_vfs_minimal.sh` | минимальная VFS |
| `test_vfs_several_files.sh` | VFS из нескольких файлов |
| `test_vfs_deep.sh` | VFS с вложенностью 3+ уровней |
| `test_vfs_errors.sh` | ошибки загрузки VFS |
| `test_stage3.sh` | все команды этапов 1–3, включая ошибки (`startup_stage3.txt`) |
| `test_stage4.sh` | команды `ls`, `cd`, `du`, `date`, включая ошибки (`startup_stage4.txt`) |

## Примеры использования

Навигация по VFS (этап 4):

```
$ ./run.sh --vfs vfs/deep.json
user@host:/$ ls
bin  etc  home  tmp  var
user@host:/$ cd /home/user
user@host:/home/user$ ls -la
-       17 .bashrc
d      126 docs
d       26 projects
user@host:/home/user$ du
126	./docs
15	./projects/emulator/src
26	./projects/emulator
26	./projects
169	.
user@host:/home/user$ cd /etc/hosts
cd: /etc/hosts: Not a directory
user@host:/home/user$ date
Sun Oct 11 17:05:09 MSK 2026
user@host:/home/user$ date +%Y-%m-%d
2026-10-11
```

Интерактивный режим:

```
$ ./run.sh --vfs vfs/deep.json
[debug] vfs = /home/user/practice/vfs/deep.json
[debug] script = (not set)
user@host:/$ vfs-info
source=vfs/deep.json
directories=11
files=10
size=324
user@host:/$ vfs-tree /home/user/../../etc
/etc
├── hosts
└── passwd
user@host:/$ vfs-tree /etc/hosts/inner
vfs-tree: /etc/hosts/inner: Not a directory
user@host:/$ ls -l /home
ls: args = ['-l', '/home']
user@host:/$ cd /home/user
cd: args = ['/home/user']
user@host:/$ foo bar
foo: command not found
user@host:/$ exit 1
exit: too many arguments
user@host:/$ exit
```

Запуск со стартовым скриптом:

```
$ ./run.sh --vfs vfs/several_files.json --script scripts/startup_vfs_check.txt
[debug] vfs = /home/user/practice/vfs/several_files.json
[debug] script = /home/user/practice/scripts/startup_vfs_check.txt
user@host:/$ conf-dump
vfs=/home/user/practice/vfs/several_files.json
script=/home/user/practice/scripts/startup_vfs_check.txt
user@host:/$ vfs-info
source=vfs/several_files.json
directories=0
files=4
size=164
user@host:/$ vfs-tree /
/
├── empty.txt
├── logo.png
├── notes.md
└── readme.txt
user@host:/$ exit
```

Ошибка загрузки VFS:

```
$ ./run.sh --vfs vfs/invalid/bad_base64.json
[debug] vfs = /home/user/practice/vfs/invalid/bad_base64.json
[debug] script = (not set)
vfs: /img.bin: invalid base64 content
```
