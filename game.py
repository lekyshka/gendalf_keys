import secrets

from levels import LEVEL_CLASSES
from llm_client import LLMClient


ADJECTIVES = {
    "masculine": (
        "лунный", "северный", "золотой", "тихий", "лазурный", "морозный",
        "алый", "звёздный", "серебряный", "янтарный", "туманный", "горный",
        "древний", "сказочный", "тайный", "багровый", "синий", "весенний",
        "полярный", "грозовой",
    ),
    "feminine": (
        "лунная", "северная", "золотая", "тихая", "лазурная", "морозная",
        "алая", "звёздная", "серебряная", "янтарная", "туманная", "горная",
        "древняя", "сказочная", "тайная", "багровая", "синяя", "весенняя",
        "полярная", "грозовая",
    ),
    "neuter": (
        "лунное", "северное", "золотое", "тихое", "лазурное", "морозное",
        "алое", "звёздное", "серебряное", "янтарное", "туманное", "горное",
        "древнее", "сказочное", "тайное", "багровое", "синее", "весеннее",
        "полярное", "грозовое",
    ),
}
NOUNS = {
    "masculine": (
        "маяк", "кедр", "дельфин", "водопад", "парус", "тюльпан", "метеор",
        "компас", "ключ", "сокол", "остров", "ветер", "замок", "дракон", "сад",
        "закат", "кристалл", "ручей", "волк", "гром",
    ),
    "feminine": (
        "река", "звезда", "корона", "гавань", "волна", "ночь", "роза", "тропа",
        "нить", "капля", "долина", "вершина", "книга", "птица", "дверь", "заря",
        "комета", "песня", "сова", "туча",
    ),
    "neuter": (
        "озеро", "сияние", "солнце", "море", "небо", "утро", "пламя", "поле",
        "зеркало", "яблоко", "болото", "ущелье", "дерево", "царство", "письмо", "облако",
    ),
}


def generate_secret_parts(excluded: list[tuple[str, str]] | None = None) -> list[tuple[str, str]]:
    """Generate one unique lowercase adjective+noun password for every level."""
    excluded_parts = set(excluded or [])
    random = secrets.SystemRandom()
    adjective_indexes = random.sample(range(len(ADJECTIVES["masculine"])), len(LEVEL_CLASSES))
    used_nouns = set()
    generated = []
    for index in adjective_indexes:
        candidates = [
            (ADJECTIVES[gender][index], noun)
            for gender in ADJECTIVES
            for noun in NOUNS[gender]
            if noun not in used_nouns and (ADJECTIVES[gender][index], noun) not in excluded_parts
        ]
        adjective, noun = random.choice(candidates)
        generated.append((adjective, noun))
        used_nouns.add(noun)
    return generated


class Game:
    def __init__(self, client: LLMClient | None = None, secret_parts: list[tuple[str, str]] | None = None):
        self.client = client or LLMClient()
        self.secret_parts = secret_parts if secret_parts is not None else generate_secret_parts()
        self.levels = [klass("".join(parts), self.client) for klass, parts in zip(LEVEL_CLASSES, self.secret_parts)]
        for level, parts in zip(self.levels, self.secret_parts):
            level.secret_parts = parts

    def level(self, index: int):
        return self.levels[index]

    def public_state(self, session: dict) -> dict:
        index = session.get("level", 0)
        level = self.level(index)
        return {"level": index + 1, "total_levels": len(self.levels), "title": level.title,
                "description": level.description, "passed": bool(session.get("passed", False)),
                "finished": index == len(self.levels) - 1 and bool(session.get("passed", False))}
