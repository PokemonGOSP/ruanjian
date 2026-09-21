"""Read-only consistency summary for Engineering Skeleton V0.1."""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base  # noqa: E402
from app.db.models import domain as _domain  # noqa: E402,F401
from app.main import app  # noqa: E402

IMPLEMENTED_OPERATIONS = {
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/logout"),
    ("GET", "/api/v1/auth/me"),
}

http_methods = {"get", "post", "put", "patch", "delete"}
operations = [
    (method.upper(), path)
    for path, path_item in app.openapi()["paths"].items()
    for method in path_item
    if method in http_methods
]
implemented = [operation for operation in operations if operation in IMPLEMENTED_OPERATIONS]
contract_text = (Path(__file__).resolve().parents[2] / "docs" / "api" / "API_CONTRACT_V0_1.md").read_text(encoding="utf-8")
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
    status = "implemented" if (method, path) in IMPLEMENTED_OPERATIONS else "skeleton"
    print(f"{method:7} {path} [{status}]")
