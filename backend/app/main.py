"""FastAPI application: shared infrastructure plus the routers and errors of each module."""

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from app.core import health
from app.core.config import get_settings
from app.core.errors import register_core_error_handlers
from app.core.lifespan import create_lifespan
from app.flights.api.errors import register_flights_error_handlers
from app.flights.api.routes import router as flights_router
from app.flights.core.messaging import EVENT_BINDINGS as FLIGHTS_EVENT_BINDINGS

app = FastAPI(title=get_settings().app_name, lifespan=create_lifespan(event_bindings=FLIGHTS_EVENT_BINDINGS))

# Search results repeat the same slices in every combination: gzip shrinks them ~30x
# (a 4.5 MB round trip travels as ~140 KB).
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)

register_core_error_handlers(app)
app.include_router(health.router)

register_flights_error_handlers(app)
app.include_router(flights_router)
