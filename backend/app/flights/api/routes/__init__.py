"""HTTP endpoints of the flights module, one file per topic, under `/api/v1/flights`."""

from fastapi import APIRouter

from app.flights.api.routes.bookings import router as bookings_router
from app.flights.api.routes.places import router as places_router
from app.flights.api.routes.search import router as search_router

router = APIRouter(prefix="/api/v1/flights", tags=["flights"])
router.include_router(search_router)
router.include_router(places_router)
router.include_router(bookings_router)
