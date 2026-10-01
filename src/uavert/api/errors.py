"""One error shape for every endpoint: {"error": {"code", "message", "details"}}. Never internals."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

log = logging.getLogger("uavert.api")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: list | None = None):
        self.status, self.code, self.message, self.details = status, code, message, details or []


def error_response(status: int, code: str, message: str, details: list | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details or []}})


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(_: Request, e: ApiError):
        return error_response(e.status, e.code, e.message, e.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, e: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"], "code": err["type"]}
                   for err in e.errors()]
        return error_response(422, "validation_error", "Some request values are not valid.", details)

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, e: HTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(e.status_code, "http_error")
        return error_response(e.status_code, code, str(e.detail))

    @app.exception_handler(Exception)
    async def unexpected(_: Request, e: Exception):
        log.exception("Unhandled error")
        return error_response(500, "internal_error", "Something went wrong on our side.")
