import asyncio
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from core.settings import settings
from core.auth import TenantAuthMiddleware
from core.plugin_manager import PluginManager
from core.log import logger
from core.response import ResponseModel
from api.knowledge import router as knowledge_router


app = FastAPI()
cors_origins_whitelist = os.getenv("CORS_ORIGINS_WHITELIST", "*")
cors_origins = (
    ["*"] if cors_origins_whitelist is None else cors_origins_whitelist.split(",")
)
app.add_middleware(TenantAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers="*",
)

app.include_router(knowledge_router.router)


@app.get("/")
def home_page():
    return RedirectResponse(url=settings.WEB_URL)


@app.get("/api/health_checker", response_model=ResponseModel)
def health_checker():
    res = {"env": os.getenv("ENV"), "extra": "hello"}
    return {"success": True, "message": res}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": str(exc)},
    )


@app.on_event("startup")
async def startup_event():
    # Load task engine and database engine plugins from the plugins folder based on the configuration
    path = os.path.abspath(os.path.dirname(__file__))
    logger.info("Application started")
    PluginManager(path)
    task_engine = PluginManager().taskPlugin
    db_engine = PluginManager().dbPlugin
    if db_engine and task_engine.on_task_execute:
        await task_engine.on_task_execute(db_engine)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")


if __name__ == "__main__":
    if settings.IS_DEV:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["./"],
            reload_includes=["*.py", ".env", "./plugins/.env"],
            reload_excludes=["*.pyc", "__pycache__/*", "./logs"],
        )
    else:
        uvicorn.run(
            app, host="0.0.0.0", port=int(os.environ.get("WHISKER_SERVER_PORT", "8080"))
        )
