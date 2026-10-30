"""HTTP endpoints of the identity module, one file per topic, under `/api/v1`."""

from fastapi import APIRouter

from app.identity.api.routes.me import router as me_router
from app.identity.api.routes.oidc import router as oidc_router
from app.identity.api.routes.passwords import router as passwords_router
from app.identity.api.routes.tokens import router as tokens_router

router = APIRouter(prefix="/api/v1", tags=["identity"])
router.include_router(tokens_router)
router.include_router(passwords_router)
router.include_router(oidc_router)
router.include_router(me_router)
