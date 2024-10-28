from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi_pagination import add_pagination
from slugify import slugify

from src.config import settings
from src.routers import router
from src.common.exception import setup_exception_handlers

slugify_app_name = slugify(settings.APP_NAME)

app: FastAPI = FastAPI(
    title=settings.APP_TITLE,
    docs_url=f"/{slugify_app_name}/docs",
    redoc_url=f"/{slugify_app_name}/redoc",
    openapi_url=f"/{slugify_app_name}/openapi.json",
)


@app.get("/", include_in_schema=False)
async def read_root():
    return RedirectResponse(url=f"/{slugify_app_name}/docs")


@app.get(f"/{slugify_app_name}/@ping", tags=["DEFAULT"], summary="Check if server is available")
async def ping():
    return {"message": "pong !"}


# Add pagination to the app
app.include_router(router=router)
add_pagination(app)
setup_exception_handlers(app)
