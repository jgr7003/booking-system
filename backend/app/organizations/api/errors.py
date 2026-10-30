"""HTTP status codes of the organizations errors."""

from fastapi import FastAPI

from app.core.errors import add_error_handlers
from app.organizations.domain.errors import UnknownInstallationError


def register_organizations_error_handlers(app: FastAPI) -> None:
    """Registers how organizations errors are answered over HTTP.

    Args:
        app: The FastAPI application.
    """
    add_error_handlers(app, {UnknownInstallationError: 404})
