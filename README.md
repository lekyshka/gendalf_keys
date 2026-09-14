# Русский Gandalf Challenge

Локальная соревновательная игра из восьми уровней по prompt injection. На каждом уровне игрок общается с Гэндальфом и пытается узнать новое кодовое слово. Сложность постепенно растёт: появляются системные ограничения, детерминированные фильтры и независимые LLM-guards.

В проект входят FastAPI backend, интерфейс на HTML/CSS/JavaScript, OpenAI-compatible Groq API, сессии игроков, общий таймер и постоянный SQLite-лидерборд.

Правила для участников находятся в [PLAYER_GUIDE.md](PLAYER_GUIDE.md). Инструкция ведущего со спойлерами и ответами находится в [HOST_GUIDE.md](HOST_GUIDE.md).

## Требования

- Python 3.11 или новее;
- интернет-соединение для Groq API;
- учётная запись Groq и API-ключ;
- Git — если проект будет клонироваться или публиковаться через GitHub.

## Как создать Groq API-ключ

1. Войдите или зарегистрируйтесь в [Groq Console](https://console.groq.com/).
2. Откройте страницу [API Keys](https://console.groq.com/keys).
3. Нажмите **Create API Key**.
4. Задайте имя, например `gandalf-local`.
5. Скопируйте созданный ключ. Не публикуйте его и не отправляйте в GitHub.

Если ключ случайно попал в публичный репозиторий, сразу удалите его в Groq Console и создайте новый. Официальная инструкция: [Groq Quickstart](https://console.groq.com/docs/quickstart).

## Установка на Linux или macOS

```bash
git clone https://github.com/lekyshka/gendalf_keys.git
cd gendalf_keys
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## Установка приложения из скачанной директории
Перейдите в директорию и выполните следующие команды
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Откройте `.env` и вставьте свой ключ после `GROQ_API_KEY=`:

```env
GROQ_API_KEY=gsk_ваш_ключ
GROQ_API_KEY_FILE=.groq_api_key
GROQ_BASE_URL=https://api.groq.com/openai/v1
MAIN_MODEL=openai/gpt-oss-120b
GUARD_MODEL=qwen/qwen3.8-27b
SESSION_SECRET=замените-на-длинную-случайную-строку
LOG_LEVEL=INFO
```

Создать случайный `SESSION_SECRET` можно командой:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Скопируйте результат в `.env` после `SESSION_SECRET=`.

## Установка на Windows

В PowerShell:

```powershell
git clone https://github.com/lekyshka/gendalf_keys.git
cd gendalf_keys
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Откройте `.env`, вставьте Groq API-ключ и замените `SESSION_SECRET`.

Если PowerShell запрещает активацию окружения:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Установка приложения из скачанной директории
Перейдите в директорию и выполните следующие команды

В PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Откройте `.env`, вставьте Groq API-ключ и замените `SESSION_SECRET`.

Если PowerShell запрещает активацию окружения:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Запуск

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8080
```

Откройте `http://127.0.0.1:8080`. Команда `uvicorn` остаётся работающей в терминале — это нормально. Для остановки нажмите `Ctrl+C`.

Режим разработки с автоматической перезагрузкой:

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8080 --reload
```

## Доступ с другого устройства

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8080
```

Откройте `http://IP_КОМПЬЮТЕРА:8080` на другом устройстве в той же сети. Такой запуск открывает приложение в локальную сеть; не публикуйте порт в интернете без reverse proxy, HTTPS и дополнительной защиты.

## Настройки `.env`

| Переменная | Назначение |
|---|---|
| `GROQ_API_KEY` | Секретный ключ Groq для запросов к моделям. |
| `GROQ_API_KEY_FILE` | Локальный файл для горячей замены ключа через интерфейс. |
| `GROQ_BASE_URL` | OpenAI-compatible endpoint Groq. |
| `MAIN_MODEL` | Модель, которая играет роль Гэндальфа. |
| `GUARD_MODEL` | Модель для input/output/intent guards. |
| `SESSION_SECRET` | Ключ подписи cookie-сессий. Должен быть случайным. |
| `LOG_LEVEL` | Уровень логирования, например `INFO` или `WARNING`. |

Чтобы сменить модель, измените `MAIN_MODEL` или `GUARD_MODEL` и перезапустите backend. Доступные модели зависят от текущего каталога и доступа вашей учётной записи Groq.

## Замена Groq-ключа без перезапуска

После запуска игры нажмите **«Настройки»**, вставьте новый ключ и выберите **«Применить ключ»**. Ключ атомарно сохраняется в `.groq_api_key` и будет использован уже следующим запросом к основной или guard-модели.

В интерфейсе и backend-логах показываются только маска ключа и первые 12 символов его SHA-256 fingerprint. Полный ключ намеренно не выводится. Файл `.groq_api_key` исключён из Git.

После добавления этой функции требуется один обычный перезапуск backend. Все последующие смены ключа выполняются без остановки сервера.

## Лидерборд

Файл `leaderboard.sqlite3` создаётся автоматически рядом с `app.py`, содержит подтверждённые результаты и исключён из Git через `.gitignore`. SQLite работает в WAL-режиме с полной синхронизацией: результаты сохраняются после остановки или аварийного завершения backend.

Текущий уровень, имя и время начала хранятся в подписанной cookie браузера сроком один год. Поэтому закрытие вкладки, браузера или перезапуск backend не сбрасывает активную попытку. Для восстановления нужно открыть игру в том же браузере и не очищать данные сайта. Не меняйте `SESSION_SECRET` во время мероприятия — после его смены старые cookie перестанут проходить проверку.

Для резервного копирования остановите запись результатов на несколько секунд и скопируйте `leaderboard.sqlite3` вместе с файлами `leaderboard.sqlite3-wal` и `leaderboard.sqlite3-shm`, если они существуют.

Очистить все результаты:

```bash
sqlite3 leaderboard.sqlite3 'DELETE FROM leaderboard;'
```

Если `sqlite3` не установлен на Ubuntu/Debian:

```bash
sudo apt install sqlite3
```

## Архитектура

```text
gendelfa/
├── app.py                 # FastAPI, сессии и leaderboard API
├── config.py              # Настройки из .env
├── game.py                # Список уровней и кодовые слова
├── llm_client.py          # Единый OpenAI-compatible клиент
├── levels/                # Классы восьми уровней
├── guards/                # Input, intent, output и deterministic guards
├── static/                # HTML, CSS и JavaScript
├── tests/                 # Автоматические тесты
├── PLAYER_GUIDE.md        # Памятка участника
└── HOST_GUIDE.md          # Инструкция ведущего со спойлерами
```

`Game` создаёт восемь наследников `BaseLevel`. Переход между уровнями и проверка пароля выполняются backend-сессией. Главная модель вызывается через `generate_main()`, guards — через `run_guard()` с температурой `0`. При ошибке guard блокирует запрос или ответ по принципу fail closed.

Пароли не возвращаются через `/api/state`. API-ключ и открытые пароли не должны попадать в логи.

## Тесты

```bash
pytest -q
```

Тесты используют fake-клиент и не расходуют лимит Groq API.

## Публикация в GitHub

Публичный репозиторий содержит безопасный `.env` без API-ключа. Перед публикацией всегда проверяйте, что `GROQ_API_KEY` в нём пустой. `.gitignore` исключает SQLite-базу, виртуальные окружения, Python-кэши и настройки редакторов.

```bash
git init
git status --short
git add .
git status --short
git commit -m "Initial Gandalf game"
git branch -M main
```

В подготовленных файлах не должно быть `leaderboard.sqlite3`, `.venv` или `.venv-llm`. Файл `.env` допустим только с пустым `GROQ_API_KEY` и шаблонным `SESSION_SECRET`.

Создайте пустой репозиторий на GitHub, затем выполните:

```bash
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

Никогда не коммитьте заполненный `GROQ_API_KEY`. Для размещённой версии приложения храните ключ в секретах платформы развёртывания, а не в GitHub.
