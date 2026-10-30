"""Read-only consistency summary for Engineering Skeleton V0.1."""

import inspect
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.routing import APIRoute  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.models import domain as _domain  # noqa: E402,F401
from app.main import app  # noqa: E402

http_methods = {"get", "post", "put", "patch", "delete"}
operations = [
    (method.upper(), path)
    for path, path_item in app.openapi()["paths"].items()
    for method in path_item
    if method in http_methods
]
route_map = {
    (method.upper(), route.path): route
    for route in app.routes
    if isinstance(route, APIRoute)
    for method in route.methods
    if method.lower() in http_methods
}


def is_skeleton(operation: tuple[str, str]) -> bool:
    route = route_map.get(operation)
    if route is None:
        return False
    return "todo(" in inspect.getsource(route.endpoint)


implemented = [operation for operation in operations if not is_skeleton(operation)]
contract_path = Path(__file__).resolve().parents[2] / "docs" / "api" / "API_CONTRACT_V0_1.md"
contract_text = contract_path.read_text(encoding="utf-8")
contract_operations = {
    (method, path if path.startswith("/api/v1") else f"/api/v1{path}")
    for method, path in re.findall(r"^\| (GET|POST|PATCH|PUT|DELETE) \| `([^`]+)`", contract_text, re.MULTILINE)
}

print(f"TABLES={len(Base.metadata.tables)}")
print(f"ENDPOINTS={len(operations)}")
print(f"IMPLEMENTED={len(implemented)}")
print(f"SKELETON={len(operations) - len(implemented)}")
print(f"CONTRACT_MISSING={sorted(set(operations) - contract_operations)}")
print(f"CONTRACT_EXTRA={sorted(contract_operations - set(operations))}")
for method, path in sorted(operations, key=lambda item: (item[1], item[0])):
    status = "skeleton" if is_skeleton((method, path)) else "implemented"
    print(f"{method:7} {path} [{status}]")
