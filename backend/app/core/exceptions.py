from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class AppError(Exception):
    def __init__(self, code: int, message: str, status_code: int, data: Any = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(message)


def error_response(status_code: int, code: int, message: str, data: Any = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "message": message, "data": data})


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message, exc.data)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(422, 40001, "请求参数校验失败", exc.errors())

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(_: Request, __: SQLAlchemyError) -> JSONResponse:
        return error_response(503, 50001, "数据库暂不可用")

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, __: Exception) -> JSONResponse:
        return error_response(500, 50000, "服务器内部错误")
