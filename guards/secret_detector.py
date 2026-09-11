class SecretDetector:
    """Намеренно простой фильтр полного пароля для уровней 3, 5 и 7."""
    @staticmethod
    def leaks(text: str, secret: str) -> bool:
        return secret.casefold() in text.casefold()
