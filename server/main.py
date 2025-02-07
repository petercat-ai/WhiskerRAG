import asyncio
import os
from core.settings import settings
import uvicorn

from core.auth import TenantAuthMiddleware
from core.plugin_manager import PluginManager
from core.log import logger
from core.response import ResponseModel
from api.knowledge import router as knowledge_router
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware


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
    # 读取配置加载 plugins 文件夹下的 任务引擎、数据引擎插件
    path = os.path.abspath(os.path.dirname(__file__))
    logger.info("Application started")
    PluginManager(path)
    task_engine = PluginManager().taskPlugin
    if task_engine.process_message_queue:
        asyncio.create_task(task_engine.process_message_queue())


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")


if __name__ == "__main__":
    if settings.IS_DEV:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,  # 开启热重载
            reload_dirs=["./"],  # 指定监听的目录
            reload_includes=["*.py", ".env", "./plugins/.env"],  # 指定监听的文件类型
            reload_excludes=["*.pyc", "__pycache__/*", "./logs"],  # 排除的文件/目录
        )
    else:
        uvicorn.run(
            app, host="0.0.0.0", port=int(os.environ.get("WHISKER_SERVER_PORT", "8080"))
        )
