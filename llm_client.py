import httpx
import time

from config import settings


class LLMError(RuntimeError):
    pass


class LLMRateLimitError(LLMError):
    pass


class LLMClient:
    def __init__(self, base_url: str = settings.groq_base_url, api_key: str = settings.groq_api_key,
                 main_model: str = settings.main_model, guard_model: str = settings.guard_model,
                 timeout: float = 30):
        self.base_url, self.api_key = base_url, api_key
        self.main_model, self.guard_model, self.timeout = main_model, guard_model, timeout

    def generate_main(self, system: str, user: str, temperature: float = 0.7) -> str:
        return self._request(self.main_model, system, user, temperature)

    def run_guard(self, system: str, user: str) -> str:
        return self._request(self.guard_model, system, user, temperature=0)

    def _request(self, model: str, system: str, user: str, temperature: float) -> str:
        if not self.api_key:
            raise LLMError("GROQ_API_KEY is not configured")
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
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
