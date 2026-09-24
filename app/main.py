import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import init_db
from .gemini_generator import close_gemini_client
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):

    # ---------------------------------------------
    # Startup
    # ---------------------------------------------

    init_db()

    yield

    # ---------------------------------------------
    # Shutdown
    # ---------------------------------------------

    close_gemini_client()


settings = get_settings()


logging.basicConfig(
    level=getattr(
        logging,
        settings.log_level.upper(),
        logging.INFO,
    )
)


app = FastAPI(
    title=settings.app_name,

    description=(
        "AI fitness plan generator "
        "using Google Gemini."
    ),

    version="1.0.0",

    lifespan=lifespan,
)


app.mount(
    "/static",
    StaticFiles(
        directory="app/static"
    ),
    name="static",
)


app.include_router(router)