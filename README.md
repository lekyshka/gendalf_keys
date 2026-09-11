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
git clone https://github.com/USERNAME/REPOSITORY.git
cd REPOSITORY
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Откройте `.env` и замените `your_groq_api_key` своим ключом:

```env
GROQ_API_KEY=gsk_ваш_ключ
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
git clone https://github.com/USERNAME/REPOSITORY.git
cd REPOSITORY
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
| `GROQ_BASE_URL` | OpenAI-compatible endpoint Groq. |
| `MAIN_MODEL` | Модель, которая играет роль Гэндальфа. |
| `GUARD_MODEL` | Модель для input/output/intent guards. |
| `SESSION_SECRET` | Ключ подписи cookie-сессий. Должен быть случайным. |
| `LOG_LEVEL` | Уровень логирования, например `INFO` или `WARNING`. |

Чтобы сменить модель, измените `MAIN_MODEL` или `GUARD_MODEL` и перезапустите backend. Доступные модели зависят от текущего каталога и доступа вашей учётной записи Groq.

## Лидерборд

Файл `leaderboard.sqlite3` создаётся автоматически при первом запуске. Он содержит локальные результаты и исключён из Git через `.gitignore`.

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

`.gitignore` уже исключает `.env`, SQLite-базу, виртуальные окружения, Python-кэши и настройки редакторов.

```bash
git init
git status --short
git add .
git status --short
git commit -m "Initial Gandalf game"
git branch -M main
```

В подготовленных файлах не должно быть `.env`, `leaderboard.sqlite3`, `.venv` или `.venv-llm`.

Создайте пустой репозиторий на GitHub, затем выполните:

```bash
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

Не используйте `git add -f .env`. Настоящий API-ключ должен существовать только в локальном `.env` или в секретах платформы развёртывания.
