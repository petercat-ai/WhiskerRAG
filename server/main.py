import os
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from api.api_key import router as api_key_router
from api.chunk import router as chunk_router
from api.knowledge import router as knowledge_router
from api.retrieval import router as retrieval_router
from api.rule import router as rule_router
from api.space import router as space_router
from api.task import router as task_router
from api.tenant import router as tenant_router
from core.log import logger, setup_logging
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from core.retrieval_counter import (
    initialize_retrieval_counter,
    shutdown_retrieval_counter,
)
from core.settings import settings
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from whiskerrag_utils import init_register


def resolve_plugin_path() -> str:
    env_path = settings.PLUGIN_PATH
    if not env_path:
        return str(Path.cwd() / "plugins")
    path = Path(env_path)
    if path.is_absolute():
        return str(path.resolve())

    return str((Path.cwd() / path).resolve())


async def startup_event() -> None:
    try:
        # 获取插件实例
        plugin_manager = PluginManager()
        db_plugin = plugin_manager.dbPlugin
        task_plugin = plugin_manager.taskPlugin
        
        # 检查插件是否已加载
        if db_plugin is None:
            raise Exception("Database plugin not found or failed to load")
        if task_plugin is None:
            raise Exception("Task engine plugin not found or failed to load")

        # 初始化插件（仅做业务逻辑初始化，不注册middleware）
        await db_plugin.ensure_initialized()
        await task_plugin.ensure_initialized(db_plugin)

        # 初始化retrieval counter
        initialize_retrieval_counter()

        logger.info("App startup event success")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


async def shutdown_event() -> None:
    try:
        # Shutdown retrieval counter first
        try:
            shutdown_retrieval_counter()
        except Exception as e:
            logger.warning(f"Error during retrieval counter shutdown: {e}")

        # Then cleanup dbPlugin
        try:
            db_plugin = PluginManager().dbPlugin
            if db_plugin:
                await db_plugin.cleanup()
        except Exception as e:
            logger.warning(f"Error during dbPlugin cleanup: {e}")

        logger.info("Application shutdown")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    await startup_event()
    try:
        yield
    finally:
        await shutdown_event()


def create_app() -> FastAPI:
    """创建并配置FastAPI应用"""
    
    # 初始化日志和基础设置
    log_dir = os.getenv("LOG_DIR", "./logs")
    setup_logging("whisker", log_dir)
    init_register("whiskerrag_utils")
    
    # 创建FastAPI应用
    app = FastAPI(lifespan=lifespan, title="whisker rag server", version="1.0.5")
    
    # 初始化插件管理器
    plugin_abs_path = resolve_plugin_path()
    logger.info(f"plugin_abs_path: {plugin_abs_path}")
    plugin_manager = PluginManager(plugin_abs_path)
    
    # 让插件管理器设置应用（包括middleware）
    plugin_manager.setup_plugins(app)
    
    # 添加异常处理器
    @app.exception_handler(404)
    async def http404_error_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=404,
            content=ResponseModel(
                success=False, message=exc.detail, data=None
            ).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        error_message = str(exc.detail) if isinstance(exc.detail, str) else str(exc)

        logger.error(
            f"HTTPException occurred: "
            f"Path={request.url.path}, Method={request.method}, "
            f"Status Code={exc.status_code}, Message={error_message}, "
            f"Traceback={traceback.format_exc()}"
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=ResponseModel(
                success=False, message=error_message, data=None
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        error_message = str(exc)

        logger.error(
            f"Global exception occurred: "
            f"Path={request.url.path}, Method={request.method}, "
            f"Exception Type={type(exc).__name__}, Message={error_message}, "
            f"Traceback={traceback.format_exc()}"
        )

        return JSONResponse(
            status_code=500,
            content=ResponseModel(
                success=False, message="Internal Server Error", data=None
            ).model_dump(),
        )

    # 添加CORS中间件
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

    # 包含路由
    app.include_router(knowledge_router.router)
    app.include_router(retrieval_router.router)
    app.include_router(task_router.router)
    app.include_router(chunk_router.router)
    app.include_router(tenant_router.router)
    app.include_router(space_router.router)
    app.include_router(rule_router.router)
    app.include_router(api_key_router.router)

    # 添加基础路由
    @app.get("/")
    def home_page() -> RedirectResponse:
        return RedirectResponse(url=settings.WEB_URL)

    @app.get("/api/health_checker", response_model=ResponseModel)
    def health_checker() -> ResponseModel[dict]:
        res = {"env": os.getenv("ENV"), "extra": "hello"}
        logger.debug(f"health check: {res}")
        return ResponseModel(success=True, data=res)

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    if settings.IS_DEV:
        plugin_abs_path = resolve_plugin_path()
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8002,
            reload=True,
            reload_dirs=["./"],
            reload_includes=["*.py", ".env", plugin_abs_path],
            reload_excludes=["*.pyc", "__pycache__/*", "./logs"],
        )
    else:
        uvicorn.run(
            app, host="0.0.0.0", port=int(os.environ.get("WHISKER_SERVER_PORT", "8080"))
        )
