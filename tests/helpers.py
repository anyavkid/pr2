"""Общие вспомогательные функции для тестов."""
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
LOCAL_REPO = (FIXTURES / "repo").as_uri()
APP = "org.example:app:1.0"
LIBA = "org.example:liba:1.0"
LIBB = "org.example:libb:2.0"
LIBC = "org.example:libc:1.0"
