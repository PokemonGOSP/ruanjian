from typing import NoReturn

from app.core.exceptions import AppError


def todo(fr: str, owner: str) -> NoReturn:
    raise AppError(50101, f"{fr} route skeleton；TODO({owner})", 501)
