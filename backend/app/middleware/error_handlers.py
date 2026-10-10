from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.api_exceptions import APIException


logger = logging.getLogger(__name__)


def register_error_handlers(
    app: FastAPI,
) -> None:

    @app.exception_handler(APIException)
    async def api_exception_handler(
        request: Request,
        exc: APIException,
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "errors": [
                    {
                        "code": exc.code,
                        "message": exc.message,
                    }
                ],
            },
        )

    @app.exception_handler(
        RequestValidationError
    )
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        errors = []

        for error in exc.errors():
            location = error.get(
                "loc",
                [],
            )

            field = ".".join(
                str(item)
                for item in location
            )

            errors.append(
                {
                    "code": "VALIDATION_ERROR",
                    "message": error.get(
                        "msg",
                        "Invalid value.",
                    ),
                    "field": field,
                }
            )

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Request validation failed.",
                "errors": errors,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ):
        logger.exception(
            "Unhandled API exception.",
            exc_info=exc,
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal server error.",
                "errors": [
                    {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": (
                            "An unexpected error occurred."
                        ),
                    }
                ],
            },
        )