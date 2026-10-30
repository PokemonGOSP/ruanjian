"""统一异常响应的结构、状态码和日志。"""

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.exceptions import AppError, install_exception_handlers


def build_client() -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/app-error")
    def raise_app_error():
        raise AppError(40302, "没有该社团的 R02 权限", 403)

    @app.get("/db-error")
    def raise_db_error():
        raise OperationalError("SELECT 1", {}, Exception("database down"))

    @app.get("/unexpected")
    def raise_unexpected():
        raise RuntimeError("boom")

    return TestClient(app, raise_server_exceptions=False)


def test_app_error_uses_envelope():
    response = build_client().get("/app-error")
    assert response.status_code == 403
    assert response.json() == {
        "code": 40302,
        "message": "没有该社团的 R02 权限",
        "data": None,
    }


def test_database_error_returns_503_and_logs(caplog):
    with caplog.at_level(logging.ERROR):
        response = build_client().get("/db-error")
    assert response.status_code == 503
    assert response.json()["code"] == 50001
    assert "数据库操作失败" in caplog.text


def test_unexpected_error_returns_500_and_logs(caplog):
    with caplog.at_level(logging.ERROR):
        response = build_client().get("/unexpected")
    assert response.status_code == 500
    assert response.json()["code"] == 50000
    assert "未预期服务端错误" in caplog.text
