# pip-dependency-grapher

Инструмент командной строки для визуализации графа зависимостей пакетов Python (формат pip).

## 1. Общее описание

Инструмент строит граф зависимостей заданного пакета (с учётом транзитивных зависимостей) и
визуализирует его: формирует описание графа на языке PlantUML, показывает изображение и, если
включено в настройках, выводит зависимости в виде ASCII-дерева. Зависимости получаются
собственным кодом по URL репозитория пакетов, без `pip` и сторонних библиотек. Все настройки
читаются из конфигурационного файла в формате INI.

Требования: **Python 3.10 или новее**, больше ничего устанавливать не нужно (используется только
стандартная библиотека). Работает на Linux, macOS и Windows. Для получения данных из репозитория и
показа изображения нужен доступ в интернет и браузер.

Состояние проекта по этапам:

| Этап | Описание | Статус |
|------|----------|--------|
| 1 | Минимальный прототип с конфигурацией (INI) | выполнен |
| 2 | Сбор данных о прямых зависимостях | выполнен |
| 3 | Граф зависимостей: BFS, глубина, циклы, тестовый режим | выполнен |
| 4 | Обратные зависимости | выполнен |
| 5 | Визуализация (PlantUML, ASCII-дерево) | выполнен |

Что делает программа при запуске:

1. Читает и проверяет конфигурацию.
2. Строит граф зависимостей.
3. Выводит текст диаграммы на языке PlantUML (между `@startuml` и `@enduml`).
4. Если `ascii_tree = true`, выводит зависимости в виде ASCII-дерева.
5. Выводит адрес изображения графа и открывает его в браузере.

Как строится граф: обход в ширину (BFS) без рекурсии, с очередью. Начальный пакет находится на
глубине 0, его прямые зависимости на глубине 1 и так далее. Зависимости пакетов запрашиваются,
пока глубина пакета меньше `max_depth`; пакеты на границе глубины попадают в граф, но показываются
без зависимостей (их зависимости не анализируются). Каждый пакет обрабатывается один раз, поэтому
циклические зависимости (включая зависимость пакета от самого себя) не приводят к зацикливанию,
а ребро, замыкающее цикл, остаётся в графе.

Как получаются зависимости в обычном режиме: программа отправляет HTTP-запрос (модуль `urllib`
из стандартной библиотеки) по адресу `<repository>/<package_name>/json`, например
`https://pypi.org/pypi/requests/json`. В ответе берётся список `info.requires_dist` (строки
`Requires-Dist` из метаданных пакета), из каждой строки выделяется имя зависимости. Имена
приводятся к единому виду (строчные буквы, подряд идущие `-`, `_`, `.` заменяются на `-`), чтобы
один и тот же пакет не попадал в граф дважды под разными написаниями. Зависимости, нужные только
для необязательных возможностей пакета (в условии указано `extra`), не учитываются. Условия
окружения (версия Python, операционная система) не вычисляются: такие зависимости учитываются.
Берётся последняя версия пакета.

Как показывается изображение: текст PlantUML сжимается (deflate), кодируется алфавитом PlantUML и
вставляется в адрес `https://www.plantuml.com/plantuml/svg/<текст>`. Адрес выводится на экран и
открывается в браузере, а картинку рисует публичный сервер PlantUML. Это значит, что названия
пакетов графа отправляются на этот сервер. Если браузер не открылся, откройте адрес вручную.

## 2. Описание всех функций и настроек

### Настройки

Параметры задаются в секции `[dependency-graph]` INI-файла (пример: `config.ini`).
Файл должен быть в кодировке UTF-8. Все пять параметров обязательны. Неизвестные параметры
считаются ошибкой, чтобы опечатки в именах не оставались незамеченными.

- `package_name` (строка): имя анализируемого пакета.
  В обычном режиме: латинские буквы, цифры, `.`, `_`, `-`.
  В тестовом режиме: большие латинские буквы (`A`, `B`, ...).
- `repository` (URL или путь): в обычном режиме URL репозитория (`http://` или `https://`),
  например `https://pypi.org/pypi`; в тестовом режиме путь к файлу тестового репозитория
  (должен существовать и быть читаемым). Относительные пути считаются от текущей папки.
- `test_mode` (`true` / `false`): режим работы с тестовым репозиторием. При `true` зависимости
  берутся не из интернета, а из файла, путь к которому указан в `repository`.
- `ascii_tree` (`true` / `false`): дополнительно вывести зависимости в виде ASCII-дерева.
- `max_depth` (целое число, не меньше 1): максимальная глубина анализа зависимостей.
  Глубина 1 означает только прямые зависимости начального пакета.

Значения `package_name` и `repository` проверяются в зависимости от `test_mode`, поэтому при
некорректном `test_mode` их формат проверяется только после его исправления.

### Формат файла тестового репозитория

Одна строка на пакет: `A: B C` означает, что пакет `A` зависит от `B` и `C`; `D:` означает, что
у `D` нет зависимостей. Имена пакетов состоят из больших латинских букв. Пустые строки
пропускаются. Пакет, который только упомянут в списке зависимостей, считается пакетом без
зависимостей. Готовые примеры лежат в папке `tests/data`.

### Формат вывода

Диаграмма PlantUML: каждый пакет объявляется компонентом `[пакет]`, каждая зависимость
выводится стрелкой `[пакет] --> [зависимость]`.

ASCII-дерево: корень — анализируемый пакет, ветви обозначены символами `+--`, `` `-- `` и `|`.
Общая зависимость показывается под каждым пакетом, который от неё зависит. Пакет, который уже
встречался на пути от корня, помечается `(цикл)` и дальше не раскрывается.

### Опции командной строки

| Опция | Описание |
|-------|----------|
| `-c`, `--config ПУТЬ` | Путь к INI-файлу (по умолчанию `config.ini` в текущей папке) |
| `-h`, `--help` | Справка |

### Обработка ошибок

Все найденные проблемы конфигурации выводятся за один запуск в поток ошибок (stderr), код
завершения равен `2`. Если не удалось получить данные (пакет не найден в репозитории или в
тестовом файле, сервер недоступен, превышено время ожидания, ответ не в формате JSON, ошибка
формата тестового файла), выводится сообщение об ошибке, код завершения равен `1`.
При успешном запуске код завершения равен `0`. Проверяются:

- наличие, читаемость и кодировка файла, корректность INI-синтаксиса, наличие секции;
- наличие каждого из пяти параметров и отсутствие неизвестных параметров;
- непустое и допустимое имя пакета (с учётом режима);
- корректность URL (схема, хост, порт) или существование и читаемость файла тестового репозитория;
- значения `true` / `false` для логических параметров;
- целое число не меньше 1 для `max_depth`.

### Функции

| Модуль | Функция / класс | Назначение |
|--------|-----------------|------------|
| `depgraph.cli` | `main(argv)` | Точка входа: читает конфигурацию, строит и показывает граф |
| `depgraph.cli` | `build_parser()` | Создаёт разбор опций командной строки |
| `depgraph.cli` | `prepare_source(config)` | Выбирает источник зависимостей: репозиторий или файл |
| `depgraph.cli` | `show_graph(graph, start, ascii_tree)` | Выводит PlantUML, дерево и открывает изображение |
| `depgraph.cli` | `report_errors(error)` | Печатает список проблем конфигурации в stderr |
| `depgraph.graph` | `build_graph(start, max_depth, get_dependencies)` | Строит граф обходом в ширину |
| `depgraph.plantuml` | `format_plantuml(graph)` | Формирует текст диаграммы PlantUML |
| `depgraph.plantuml` | `encode_plantuml(text)` | Сжимает и кодирует текст для адреса сервера |
| `depgraph.plantuml` | `build_image_url(text)` | Возвращает адрес изображения диаграммы |
| `depgraph.tree` | `format_tree(graph, start)` | Строит ASCII-дерево зависимостей |
| `depgraph.graph_file` | `read_test_repository(path)` | Читает файл тестового репозитория |
| `depgraph.graph_file` | `parse_test_repository(text)` | Разбирает текст описания графа |
| `depgraph.graph_file` | `get_test_dependencies(graph, package)` | Прямые зависимости пакета из тестового файла |
| `depgraph.dependencies` | `get_direct_dependencies(repository, package)` | Возвращает имена прямых зависимостей |
| `depgraph.dependencies` | `normalize_name(name)` | Приводит имя пакета к единому виду |
| `depgraph.dependencies` | `build_url(repository, package)` | Формирует адрес метаданных пакета |
| `depgraph.dependencies` | `fetch_metadata(url)` | Скачивает и разбирает JSON с метаданными |
| `depgraph.dependencies` | `extract_requirements(metadata)` | Достаёт список `Requires-Dist` |
| `depgraph.dependencies` | `parse_requirement(line)` | Выделяет имя зависимости из строки |
| `depgraph.dependencies` | `FetchError` | Исключение для ошибок получения данных |
| `depgraph.config` | `load_config(path)` | Читает INI-файл и возвращает проверенный `Config` |
| `depgraph.config` | `Config` | Неизменяемый набор параметров |
| `depgraph.config` | `ConfigError` | Исключение со списком проблем (`problems`) |
| `depgraph.config` | `read_section(path)` | Читает файл и возвращает секцию параметров |
| `depgraph.config` | `parse_*`, `check_*` | Проверка значений отдельных параметров |

## 3. Команды для сборки и запуска тестов

Сборка не требуется: проект написан на чистом Python и не имеет внешних зависимостей.
Код находится в папке `src`, поэтому при запуске нужно добавлять её в `PYTHONPATH`
(это делают `Makefile` и `run.bat`).

**Linux и macOS** (нужен `make`; в Ubuntu: `sudo apt install make`):

```bash
make run                      # запуск с config.ini
make run CONFIG=my.ini        # запуск с другим файлом
make test                     # запуск тестов
make clean                    # удалить служебные файлы Python
```

То же без `make`:

```bash
PYTHONPATH=src python3 -m depgraph --config config.ini
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

**Windows, командная строка (cmd)**:

```bat
run.bat
run.bat --config my.ini
run.bat test
```

**Windows, PowerShell**:

```powershell
$env:PYTHONPATH = "src"
python -m depgraph --config config.ini
python -m unittest discover -s tests -v
```

На Windows интерпретатор обычно называется `python` (или `py`), на Linux и macOS — `python3`.

## 4. Примеры использования

### Три реальных пакета

Запуск с `repository = https://pypi.org/pypi`, `test_mode = false`, `ascii_tree = true`,
`max_depth = 3`, Python 3.14, Linux. Адрес изображения сокращён.

Пакет `requests` (только прямые зависимости):

```text
@startuml
[requests]
[charset-normalizer]
[idna]
[urllib3]
[certifi]
[requests] --> [charset-normalizer]
[requests] --> [idna]
[requests] --> [urllib3]
[requests] --> [certifi]
@enduml
requests
+-- charset-normalizer
+-- idna
+-- urllib3
`-- certifi
Изображение графа: https://www.plantuml.com/plantuml/svg/SoWkIImgAStDuOekIYqiJIqkAOxbYax...
```

Пакет `flask` (общая зависимость `markupsafe`, вложенные зависимости):

```text
@startuml
[flask]
[blinker]
[click]
[importlib-metadata]
[itsdangerous]
[jinja2]
[markupsafe]
[werkzeug]
[zipp]
[lazy-importer]
[flask] --> [blinker]
[flask] --> [click]
[flask] --> [importlib-metadata]
[flask] --> [itsdangerous]
[flask] --> [jinja2]
[flask] --> [markupsafe]
[flask] --> [werkzeug]
[importlib-metadata] --> [zipp]
[importlib-metadata] --> [lazy-importer]
[jinja2] --> [markupsafe]
[werkzeug] --> [markupsafe]
@enduml
flask
+-- blinker
+-- click
+-- importlib-metadata
|   +-- zipp
|   `-- lazy-importer
+-- itsdangerous
+-- jinja2
|   `-- markupsafe
+-- markupsafe
`-- werkzeug
    `-- markupsafe
Изображение графа: https://www.plantuml.com/plantuml/svg/TL593eCm3Bpp2ZwGInzGyG_KWo46XIn4M...
```

Пакет `pytest` (зависимости с условиями окружения):

```text
@startuml
[pytest]
[colorama]
[exceptiongroup]
[iniconfig]
[packaging]
[pluggy]
[pygments]
[tomli]
[typing-extensions]
[pytest] --> [colorama]
[pytest] --> [exceptiongroup]
[pytest] --> [iniconfig]
[pytest] --> [packaging]
[pytest] --> [pluggy]
[pytest] --> [pygments]
[pytest] --> [tomli]
[exceptiongroup] --> [typing-extensions]
@enduml
pytest
+-- colorama
+-- exceptiongroup
|   `-- typing-extensions
+-- iniconfig
+-- packaging
+-- pluggy
+-- pygments
`-- tomli
Изображение графа: https://www.plantuml.com/plantuml/svg/PP3H3SCW34J_CqKMO8KgUqJvGDIrh891O...
```

### Сравнение со штатными инструментами

В `pip` нет команды, которая рисует дерево зависимостей. Для сравнения использованы:

- сам `pip`: при установке он выводит строки `Requirement already satisfied: ... (from пакет)`
  для каждой прямой зависимости, которую учёл;
- `pipdeptree` (не входит в `pip`, но это стандартная утилита для вывода дерева зависимостей).

Окружение: Python 3.14, Linux, версии requests 2.34.2, Flask 3.1.3, pytest 9.2.0,
pipdeptree 4.2.14. Вывод `pipdeptree -p <пакет>`:

```text
requests==2.34.2
┣━━ ✓ certifi required: >=2023.5.7 installed: 2026.10.23
┣━━ ✓ charset-normalizer required: >=2,<4 installed: 3.5.2
┣━━ ✓ idna required: >=2.5,<4 installed: 3.20
┗━━ ✓ urllib3 required: >=1.26,<3 installed: 2.8.0

Flask==3.1.3
┣━━ ✓ blinker required: >=1.9.0 installed: 1.9.0
┣━━ ✓ click required: >=8.1.3 installed: 8.5.1
┣━━ ✓ itsdangerous required: >=2.2.0 installed: 2.2.0
┣━━ ✓ Jinja2 required: >=3.1.2 installed: 3.1.6
┃   ┗━━ ✓ MarkupSafe required: >=2.0 installed: 3.0.4
┣━━ ✓ MarkupSafe required: >=2.1.1 installed: 3.0.4
┗━━ ✓ Werkzeug required: >=3.1.0 installed: 3.1.9
    ┗━━ ✓ MarkupSafe required: >=2.1.1 installed: 3.0.4

pytest==9.2.0
┣━━ ✓ iniconfig required: >=2 installed: 2.3.1
┣━━ ✓ packaging required: >=24 installed: 26.3
┣━━ ✓ pluggy required: >=1.6,<2 installed: 1.7.0
┗━━ ✓ Pygments required: >=2.15 installed: 2.21.0
```

Результаты `pip` совпадают с `pipdeptree`: для `requests` он учёл certifi, charset_normalizer, idna,
urllib3; для `flask` — blinker, click, itsdangerous, jinja2, markupsafe, werkzeug; для `pytest` —
iniconfig, packaging, pluggy, pygments.

| Пакет | Состав зависимостей | Расхождение |
|-------|---------------------|-------------|
| `requests` | совпадает | нет |
| `flask` | у нас дополнительно `importlib-metadata`, `zipp`, `lazy-importer` | есть |
| `pytest` | у нас дополнительно `colorama`, `exceptiongroup`, `tomli`, `typing-extensions` | есть |

Для `flask` и `pytest` остальная часть графа (включая общую зависимость `markupsafe`, которая
встречается под `jinja2`, `werkzeug` и напрямую у `flask`) совпадает с `pipdeptree`.

Причины расхождений:

1. **Условия окружения.** Дополнительные пакеты есть в нашем выводе, но `pip` и `pipdeptree`
   их не учитывают. Наш инструмент отбрасывает только зависимости для `extra` и не вычисляет
   остальные условия (версия Python, операционная система). `pip` и `pipdeptree` проверяют эти
   условия для текущего окружения (Python 3.14, Linux). Каждый лишний пакет либо сам имеет
   условие, которое здесь не выполняется, либо подключён через такой пакет (`zipp` и
   `lazy-importer` через `importlib-metadata`, `typing-extensions` через `exceptiongroup`),
   поэтому `pip` их не ставит. Наш граф показывает все возможные зависимости пакета независимо
   от окружения, а штатные инструменты только те, что реально установлены. На другой версии
   Python или другой системе вывод `pipdeptree` изменится, а наш останется прежним.
2. **Написание имён.** Мы приводим имена к единому виду (строчные буквы), `pipdeptree` показывает
   имена так, как их указал автор: `Flask`, `Jinja2`, `MarkupSafe`, `Werkzeug`, `Pygments`.
3. **Порядок.** Мы выводим зависимости в порядке метаданных пакета, `pipdeptree` сортирует
   их по алфавиту.
4. **Версии.** `pipdeptree` показывает требуемые и установленные версии. Наш инструмент
   показывает только имена пакетов (последняя версия из репозитория, версии в граф не входят).

### Тестовый репозиторий и ошибки

Во всех примерах тестового режима `test_mode = true` и `package_name = A`, а `repository` указывает
на файл из `tests/data`. Адрес изображения в примерах сокращён.

Общая зависимость (`tests/data/diamond.txt`: `A: B C`, `B: D`, `C: D`, `D: E`, `E:`),
`ascii_tree = true`, `max_depth = 5`:

```text
@startuml
[A]
[B]
[C]
[D]
[E]
[A] --> [B]
[A] --> [C]
[B] --> [D]
[C] --> [D]
[D] --> [E]
@enduml
A
+-- B
|   `-- D
|       `-- E
`-- C
    `-- D
        `-- E
Изображение графа: https://www.plantuml.com/plantuml/svg/SoWkIImgAStDuOfsZEMATW9YP...
```

Тот же файл, `ascii_tree = true`, `max_depth = 2`. Пакет `D` на границе глубины показывается
без зависимостей:

```text
@startuml
[A]
[B]
[C]
[D]
[A] --> [B]
[A] --> [C]
[B] --> [D]
[C] --> [D]
@enduml
A
+-- B
|   `-- D
`-- C
    `-- D
Изображение графа: https://www.plantuml.com/plantuml/svg/SoWkIImgAStDuOfsZEMATW9YP...
```

Цикл (`tests/data/cycle.txt`: `A: B`, `B: C`, `C: A D`, `D:`), `ascii_tree = true`,
`max_depth = 5`. Обход не зацикливается, ребро `C -> A` остаётся в графе, а в дереве пакет `A`
помечен как цикл:

```text
@startuml
[A]
[B]
[C]
[D]
[A] --> [B]
[B] --> [C]
[C] --> [A]
[C] --> [D]
@enduml
A
`-- B
    `-- C
        +-- A (цикл)
        `-- D
Изображение графа: https://www.plantuml.com/plantuml/svg/SoWkIImgAStDuOfsZEMATW9YP...
```

Пакет зависит от самого себя (`tests/data/self_loop.txt`: `A: A B`, `B:`), `ascii_tree = true`:

```text
@startuml
[A]
[B]
[A] --> [A]
[A] --> [B]
@enduml
A
+-- A (цикл)
`-- B
Изображение графа: https://www.plantuml.com/plantuml/svg/SoWkIImgAStDuOfsZEMATee5qG...
```

Начального пакета нет в файле (`package_name = Z`, файл `tests/data/diamond.txt`):

```text
Ошибка: пакет Z не найден в тестовом репозитории
```

Ошибка формата файла (`tests/data/bad_format.txt`, во второй строке нет двоеточия):

```text
Ошибка: строка 2: ожидается формат 'A: B C'
```

Пакет не найден в репозитории (обычный режим, `package_name = no-such-package`):

```text
Ошибка: пакет не найден в репозитории: https://pypi.org/pypi/no-such-package/json
```

Репозиторий недоступен (`repository = http://127.0.0.1:9/pypi`):

```text
Ошибка: не удалось подключиться к http://127.0.0.1:9/pypi/requests/json: [Errno 111] Connection refused
```

Файл конфигурации не найден:

```text
$ python3 -m depgraph --config no_such.ini
Ошибка конфигурации:
  - файл конфигурации не найден: no_such.ini
```

Несколько ошибок сразу (`test_mode = yes`, `ascii_tree = 2`, `max_depth = 0`, лишний параметр `max_dept`):

```text
Ошибка конфигурации:
  - test_mode: ожидается true или false, получено 'yes'
  - ascii_tree: ожидается true или false, получено '2'
  - max_depth: значение должно быть не меньше 1, получено 0
  - неизвестный параметр 'max_dept'
```

Тестовый режим: имя пакета в нижнем регистре и несуществующий файл:

```text
Ошибка конфигурации:
  - package_name: в тестовом режиме имя пакета — большие латинские буквы (A, B, ...), получено 'a'
  - repository: файл 'missing_graph.txt' не найден
```

Не заданы параметры:

```text
Ошибка конфигурации:
  - отсутствует параметр 'repository'
  - отсутствует параметр 'test_mode'
  - отсутствует параметр 'ascii_tree'
  - отсутствует параметр 'max_depth'
```

Файл без заголовка секции:

```text
Ошибка конфигурации:
  - некорректный INI-файл: в строке 1 ожидается заголовок секции [dependency-graph]
```
