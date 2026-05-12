"""Configuració dels entorns de base de dades."""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "test").lower()
_ENTORNS = {"test", "development", "production"}

if ENVIRONMENT not in _ENTORNS:
    raise ValueError(
        "ENVIRONMENT ha de ser 'test', 'development' o 'production'. "
        f"Valor rebut: {ENVIRONMENT!r}"
    )


def _obtenir_url_bbdd() -> str:
    if ENVIRONMENT == "test":
        return os.getenv("DB_URL_TEST", "sqlite:///./f1_test.db")

    variable = (
        "DB_URL_DEVELOPMENT"
        if ENVIRONMENT == "development"
        else "DB_URL_PRODUCTION"
    )
    url = os.getenv(variable)

    if not url:
        raise RuntimeError(
            f"Falta la variable d'entorn {variable}. "
            "Per development i production cal una URL de PostgreSQL."
        )

    return url


DB_URL = _obtenir_url_bbdd()
