import httpx
import hashlib
import logging
import os
import time
from pathlib import Path

from config import settings

log = logging.getLogger("gandalf.llm")


class LLMError(RuntimeError):
    pass


class LLMRateLimitError(LLMError):
    pass


def key_description(api_key: str) -> dict[str, str | bool]:
    if not api_key:
        return {"configured": False, "masked": "не настроен", "fingerprint": "—"}
    masked = f"{api_key[:4]}…{api_key[-4:]}" if len(api_key) >= 9 else "••••"
    fingerprint = hashlib.sha256(api_key.encode()).hexdigest()[:12]
    return {"configured": True, "masked": masked, "fingerprint": fingerprint}


def save_runtime_api_key(api_key: str, key_file: str = settings.groq_api_key_file) -> dict[str, str | bool]:
    api_key = api_key.strip()
    if len(api_key) < 20 or any(character.isspace() for character in api_key):
        raise ValueError("Ключ выглядит некорректно.")
    path = Path(key_file)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(api_key, encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    return key_description(api_key)


class LLMClient:
    def __init__(self, base_url: str = settings.groq_base_url, api_key: str | None = None,
                 main_model: str = settings.main_model, guard_model: str = settings.guard_model,
                 timeout: float = 30, api_key_file: str | None = None):
        self.base_url = base_url
        self.api_key = settings.groq_api_key if api_key is None else api_key
        self.api_key_file = settings.groq_api_key_file if api_key is None and api_key_file is None else api_key_file
        self.main_model, self.guard_model, self.timeout = main_model, guard_model, timeout

    def current_api_key(self) -> str:
        if self.api_key_file:
            try:
                runtime_key = Path(self.api_key_file).read_text(encoding="utf-8").strip()
                if runtime_key:
                    return runtime_key
            except FileNotFoundError:
                pass
        return self.api_key

    def generate_main(self, system: str, user: str, temperature: float = 0.7) -> str:
        return self._request(self.main_model, system, user, temperature)

    def run_guard(self, system: str, user: str) -> str:
        return self._request(self.guard_model, system, user, temperature=0)

    def _request(self, model: str, system: str, user: str, temperature: float) -> str:
        api_key = self.current_api_key()
        if not api_key:
            raise LLMError("GROQ_API_KEY is not configured")
        description = key_description(api_key)
        log.info(
            "groq_request model=%s key=%s fingerprint=%s",
            model,
            description["masked"],
            description["fingerprint"],
        )
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        for attempt in range(3):
            try:
                response = httpx.post(f"{self.base_url}/chat/completions", json=payload,
                                      headers=headers, timeout=self.timeout)
                if response.status_code == 429:
                    if attempt < 2:
                        time.sleep(0.5 * (2 ** attempt))
                        continue
                    raise LLMRateLimitError("Groq rate limit exceeded; try again shortly")
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError("content is not text")
                return content
            except LLMRateLimitError:
                raise
            except httpx.TransportError as exc:
                if attempt < 2:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise LLMError("Groq API is unavailable") from exc
            except (httpx.HTTPStatusError, KeyError, IndexError, TypeError, ValueError) as exc:
                raise LLMError("Groq API request failed") from exc
