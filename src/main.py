from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi_pagination import add_pagination
from slugify import slugify

from src.config import settings
from src.config.database import shutdown_db_client, startup_db_client
from src.routers import bucket_router, media_router
from src.common.exception import setup_exception_handlers

from src.models import Bucket, Media

slugify_app_name = slugify(settings.APP_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_db_client(app=app, models=[Bucket, Media])
    yield

    await shutdown_db_client(app=app)


app: FastAPI = FastAPI(
    lifespan=lifespan,
    title=settings.APP_TITLE,
    docs_url="/sfs/docs",
    redoc_url="/sfs/redoc",
    openapi_url="/sfs/openapi.json",
)


@app.get("/", include_in_schema=False)
async def read_root():
    return RedirectResponse(url="/sfs/docs")


@app.get("/sfs/@ping", tags=["DEFAULT"], summary="Check if server is available")
async def ping():
    return {"message": "pong !"}


# Add pagination to the app
app.include_router(router=bucket_router)
app.include_router(router=media_router)
add_pagination(app)
setup_exception_handlers(app)
