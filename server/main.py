import os
from contextlib import asynccontextmanager

import uvicorn
from api.chunk import router as chunk_router
from api.knowledge import router as knowledge_router
from api.retrieval import router as retrieval_router
from api.task import router as task_router
from api.tenant import router as tenant_router
from core.log import logger
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from core.settings import settings
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse


async def startup_event() -> None:
    # Load task engine and database engine plugins from the plugins folder based on the configuration
    path = os.path.abspath(os.path.dirname(__file__))
    logger.info(
        f"Application started with path : {path}",
    )
    PluginManager(path)
    logger.info("Task engine callback registered")


async def shutdown_event() -> None:
    logger.info("Application shutdown")


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    await startup_event()
    try:
        yield
    finally:
        await shutdown_event()


app = FastAPI(lifespan=lifespan, version="1.0.0")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Global exception handler Request path: {request.url.path}")

    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ResponseModel(success=False, message=str(exc.detail)).model_dump(),
        )

    return JSONResponse(
        status_code=500,
        content=ResponseModel(success=False, message=str(exc)).model_dump(),
    )


cors_origins_whitelist = os.getenv("CORS_ORIGINS_WHITELIST", "*")
cors_origins = (
    ["*"] if cors_origins_whitelist is None else cors_origins_whitelist.split(",")
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers="*",
)

app.include_router(knowledge_router.router)
app.include_router(retrieval_router.router)
app.include_router(task_router.router)
app.include_router(chunk_router.router)
app.include_router(tenant_router.router)


@app.get("/")
def home_page() -> RedirectResponse:
    return RedirectResponse(url=settings.WEB_URL)


@app.get("/api/health_checker", response_model=ResponseModel)
def health_checker() -> ResponseModel[dict]:
    res = {"env": os.getenv("ENV"), "extra": "hello"}
    logger.debug(f"health check: {res}")
    return ResponseModel(success=True, data=res)


if __name__ == "__main__":
    if settings.IS_DEV:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8002,
            reload=True,
            reload_dirs=["./"],
            reload_includes=["*.py", ".env", "./plugins/.env"],
            reload_excludes=["*.pyc", "__pycache__/*", "./logs"],
        )
    else:
        uvicorn.run(
            app, host="0.0.0.0", port=int(os.environ.get("WHISKER_SERVER_PORT", "8080"))
        )
