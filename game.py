from levels import LEVEL_CLASSES
from llm_client import LLMClient

SECRETS = ["лунныймаяк", "северныйкедр", "золотойдельфин", "тихийводопад", "лазурныйпарус", "морозныйтюльпан", "алыйметеор", "звёздныйкомпас"]
SECRET_PARTS = [("лунный", "маяк"), ("северный", "кедр"), ("золотой", "дельфин"), ("тихий", "водопад"), ("лазурный", "парус"), ("морозный", "тюльпан"), ("алый", "метеор"), ("звёздный", "компас")]


class Game:
    def __init__(self, client: LLMClient | None = None):
        self.client = client or LLMClient()
        self.levels = [klass(secret, self.client) for klass, secret in zip(LEVEL_CLASSES, SECRETS)]
        for level, parts in zip(self.levels, SECRET_PARTS):
            level.secret_parts = parts

    def level(self, index: int):
        return self.levels[index]

    def public_state(self, session: dict) -> dict:
        index = session.get("level", 0)
        level = self.level(index)
        return {"level": index + 1, "total_levels": len(self.levels), "title": level.title,
                "description": level.description, "passed": bool(session.get("passed", False)),
                "finished": index == len(self.levels) - 1 and bool(session.get("passed", False))}
