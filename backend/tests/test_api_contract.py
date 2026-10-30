"""Lock the OpenAPI surface to `docs/api/API_CONTRACT_V0_1.md`."""

import re
from pathlib import Path

from app.main import app

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
CONTRACT_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "api" / "API_CONTRACT_V0_1.md"
)


def _openapi_operations() -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, path_item in app.openapi()["paths"].items()
        for method in path_item
        if method in HTTP_METHODS
    }


def _contract_operations() -> set[tuple[str, str]]:
    contract_text = CONTRACT_PATH.read_text(encoding="utf-8")
    return {
        (method, path if path.startswith("/api/v1") else f"/api/v1{path}")
        for method, path in re.findall(
            r"^\| (GET|POST|PATCH|PUT|DELETE) \| `([^`]+)`",
            contract_text,
            re.MULTILINE,
        )
    }


def test_openapi_matches_api_contract():
    operations = _openapi_operations()
    contract_operations = _contract_operations()

    assert operations - contract_operations == set(), "OpenAPI 中存在契约未定义的路由"
    assert contract_operations - operations == set(), "契约中定义了 OpenAPI 未注册的路由"
    assert len(operations) == 56
