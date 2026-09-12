import hashlib
import logging
import re
import sqlite3
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from config import settings
from game import Game
from llm_client import LLMError, LLMRateLimitError, key_description, save_runtime_api_key

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("gandalf")
PROJECT_ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Русский Гэндальф: защита промптов")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    max_age=60 * 60 * 24 * 365,
)
app.mount("/static", StaticFiles(directory="static"), name="static")
game = Game()

class ChatBody(BaseModel):
    message: str
class PasswordBody(BaseModel):
    password: str

class StartGameBody(BaseModel):
    name: str

class GroqKeyBody(BaseModel):
    api_key: str


class Leaderboard:
    """Small local store for one result per finished game run."""

    def __init__(self, path: str | Path = PROJECT_ROOT / "leaderboard.sqlite3"):
        self.path = Path(path)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS leaderboard (
                    run_id TEXT PRIMARY KEY,
                    player_name TEXT NOT NULL,
                    completed_level INTEGER NOT NULL,
                    elapsed_seconds INTEGER NOT NULL,
                    updated_at REAL NOT NULL
                )"""
            )

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def record_completion(self, run_id: str, player_name: str, level: int, elapsed_seconds: int):
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO leaderboard
                    (run_id, player_name, completed_level, elapsed_seconds, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET
                        player_name = excluded.player_name,
                        completed_level = excluded.completed_level,
                        elapsed_seconds = excluded.elapsed_seconds,
                        updated_at = excluded.updated_at
                    WHERE excluded.completed_level > leaderboard.completed_level""",
                (run_id, player_name, level, elapsed_seconds, time.time()),
            )

    def entries(self):
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT player_name, completed_level, elapsed_seconds
                    FROM leaderboard
                    WHERE completed_level > 0
                    ORDER BY completed_level DESC, elapsed_seconds ASC, updated_at ASC"""
            ).fetchall()
        return [
            {"name": row[0], "level": row[1], "elapsed_seconds": row[2]}
            for row in rows
        ]


leaderboard = Leaderboard()

def current_level(request: Request):
    request.session.setdefault("level", 0)
    request.session.setdefault("passed", False)
    return game.level(request.session["level"])


def elapsed_seconds(request: Request) -> int:
    started_at = request.session.get("started_at")
    if not started_at:
        return 0
    ended_at = request.session.get("ended_at")
    return max(0, int((ended_at or time.time()) - started_at))


def public_state(request: Request):
    if not request.session.get("player_name"):
        return {
            **game.public_state({"level": 0, "passed": False}),
            "game_started": False,
            "ended": False,
            "player_name": None,
            "last_completed_level": 0,
            "elapsed_seconds": 0,
        }
    current_level(request)
    return {
        **game.public_state(request.session),
        "game_started": True,
        "ended": bool(request.session.get("ended")),
        "player_name": request.session["player_name"],
        "last_completed_level": request.session.get("last_completed_level", 0),
        "elapsed_seconds": elapsed_seconds(request),
    }


def require_active_game(request: Request):
    if not request.session.get("player_name") or request.session.get("ended"):
        raise HTTPException(status_code=409, detail="Сначала начните новую игру и укажите имя.")

def redact_secret(value: str, secret: str) -> str:
    """Keep useful development logs without persisting the current password."""
    return re.sub(re.escape(secret), "[REDACTED]", value, flags=re.IGNORECASE)

@app.get("/")
def index(): return FileResponse("static/index.html")

@app.get("/background.jpg")
def background(): return FileResponse("photo_2026-09-08_22-38-27.jpg", media_type="image/jpeg")

@app.get("/gandalf.jpg")
def gandalf_portrait(): return FileResponse("yusdzulf9bo71.jpg", media_type="image/jpeg")

@app.get("/api/state")
def state(request: Request):
    return public_state(request)

@app.get("/api/leaderboard")
def get_leaderboard():
    return {"entries": leaderboard.entries()}

@app.get("/api/settings/groq-key")
def groq_key_status():
    api_key = game.client.current_api_key()
    return key_description(api_key)

@app.post("/api/settings/groq-key")
def update_groq_key(body: GroqKeyBody):
    try:
        description = save_runtime_api_key(body.api_key)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    log.warning(
        "groq_api_key_updated key=%s fingerprint=%s",
        description["masked"],
        description["fingerprint"],
    )
    return description

@app.post("/api/start-game")
def start_game(body: StartGameBody, request: Request):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Введите имя игрока.")
    if len(name) > 40:
        raise HTTPException(status_code=422, detail="Имя должно быть не длиннее 40 символов.")
    request.session.clear()
    request.session.update({
        "player_name": name,
        "run_id": uuid.uuid4().hex,
        "started_at": time.time(),
        "ended": False,
        "last_completed_level": 0,
        "level": 0,
        "passed": False,
    })
    return public_state(request)

@app.post("/api/chat")
def chat(body: ChatBody, request: Request):
    require_active_game(request)
    level, started = current_level(request), time.perf_counter()
    prompt_hash = hashlib.sha256(body.message.encode()).hexdigest()[:12]
    log.info("chat level=%s prompt=%r prompt_hash=%s", level.number, redact_secret(body.message, level.secret), prompt_hash)
    ok, reason = level.validate_input(body.message)
    log.info("input_validation level=%s decisions=%s", level.number, reason)
    if not ok:
        log.warning("blocked level=%s reason=%s latency_ms=%.1f", level.number, reason, (time.perf_counter()-started)*1000)
        return {"reply": level.input_block_message, "blocked": True}
    try:
        reply = level.generate_response(body.message)
    except LLMRateLimitError:
        log.warning("groq_rate_limited level=%s", level.number)
        return {"reply": "Превышен лимит запросов Groq. Повторите попытку через несколько секунд.", "blocked": True}
    except LLMError:
        log.exception("main_llm_error level=%s", level.number)
        return {"reply": "Сервис Groq временно недоступен. Повторите попытку позже.", "blocked": True}
    reply = level.sanitize_output(reply)
    ok, reason = level.validate_output(reply)
    log.info("main_reply level=%s reply=%r output=%s latency_ms=%.1f", level.number, redact_secret(reply, level.secret), reason, (time.perf_counter()-started)*1000)
    if not ok:
        log.warning("blocked level=%s reason=%s", level.number, reason)
        return {"reply": level.output_block_message, "blocked": True}
    return {"reply": reply, "blocked": False}

@app.post("/api/check-password")
def check_password(body: PasswordBody, request: Request):
    require_active_game(request)
    level = current_level(request)
    correct = level.check_password(body.password)
    request.session["passed"] = correct
    if correct and level.number > request.session.get("last_completed_level", 0):
        request.session["last_completed_level"] = level.number
        leaderboard.record_completion(
            request.session["run_id"],
            request.session["player_name"],
            level.number,
            elapsed_seconds(request),
        )
    return {"correct": correct, "state": public_state(request)}

@app.post("/api/next-level")
def next_level(request: Request):
    require_active_game(request)
    current_level(request)
    if not request.session["passed"]:
        return {"advanced": False, "state": public_state(request)}
    if request.session["level"] < len(game.levels) - 1:
        request.session["level"] += 1
        request.session["passed"] = False
        return {"advanced": True, "state": public_state(request)}
    return {"advanced": False, "state": public_state(request)}

@app.post("/api/end-game")
def end_game(request: Request):
    require_active_game(request)
    request.session["ended"] = True
    request.session["ended_at"] = time.time()
    return public_state(request)

@app.post("/api/reset")
def reset(request: Request):
    request.session.clear()
    return public_state(request)
