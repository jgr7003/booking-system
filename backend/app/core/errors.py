"""Platform error base class and the uniform `{"error": {...}}` HTTP error format."""

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for errors the platform reports to clients.

    Subclasses set a stable `code` that clients can rely on. The HTTP status of each subclass is
    decided by the module that registers it (see `add_error_handlers`), not by the error itself.

    Attributes:
        message: Human-readable description, safe to show to clients.
    """

    # Machine-readable error code, e.g. `"provider_timeout"`. Each subclass sets its own.
    code = "internal_error"

    def __init__(self, message: str) -> None:
        """Initializes the error.

        Args:
            message: Human-readable description, safe to show to clients.
        """
        super().__init__(message)
        self.message = message


def error_response(status_code: int, code: str, message: str, details: list | None = None) -> JSONResponse:
    """Builds an error response in the platform's uniform format.

    Args:
        status_code: HTTP status code.
        code: Machine-readable error code.
        message: Human-readable description.
        details: Optional extra information, e.g. the fields that failed validation.

    Returns:
        A JSON response with the body `{"error": {"code", "message", "details"?}}`.
    """
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})


def add_error_handlers(app: FastAPI, status_codes: dict[type[AppError], int]) -> None:
    """Registers handlers that turn domain errors into HTTP responses.

    Each module calls this with its own errors. Handlers are resolved by the exception's MRO, so a
    subclass with its own entry wins over its parent.

    Args:
        app: The FastAPI application.
        status_codes: HTTP status code to answer for each error type.
    """
    for error_type, status_code in status_codes.items():

        async def handler(request: Request, exc: AppError, status_code: int = status_code) -> JSONResponse:
            return error_response(status_code, exc.code, exc.message)

        app.add_exception_handler(error_type, handler)


def register_core_error_handlers(app: FastAPI) -> None:
    """Registers the handlers shared by every module.

    Request validation errors become 422 `validation_error` responses with the failing fields in
    `details`; any other unhandled `AppError` becomes a 500.

    Args:
        app: The FastAPI application.
    """

    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"loc": list(e["loc"]), "message": e["msg"]} for e in exc.errors()]
        return error_response(422, "validation_error", "The request is invalid.", jsonable_encoder(details))

    app.add_exception_handler(RequestValidationError, validation_handler)
    add_error_handlers(app, {AppError: 500})
