import os
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import time

import uvicorn
from api.api_key import router as api_key_router
from api.agent import router as agent_router
from api.chunk import router as chunk_router
from api.knowledge import router as knowledge_router
from api.retrieval import router as retrieval_router
from api.rule import router as rule_router
from api.space import router as space_router
from api.task import router as task_router
from api.tenant import router as tenant_router
from core.log import logger, setup_logging, cleanup_logging
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from core.global_vars import inject_global_vars, cleanup_global_vars
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
        # init plugin manager
        plugin_manager = PluginManager()
        db_plugin = plugin_manager.dbPlugin
        task_plugin = plugin_manager.taskPlugin

        # check plugin is loaded
        if db_plugin is None:
            raise Exception("Database plugin not found or failed to load")
        if task_plugin is None:
            raise Exception("Task engine plugin not found or failed to load")

        # init plugin (only do business logic init, not register middleware)
        await db_plugin.ensure_initialized()
        await task_plugin.ensure_initialized(db_plugin)

        # init retrieval counter
        initialize_retrieval_counter()

        logger.info("App startup event success")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


async def shutdown_event() -> None:
    try:
        # shutdown retrieval counter first
        try:
            shutdown_retrieval_counter()
        except Exception as e:
            logger.warning(f"Error during retrieval counter shutdown: {e}")

        # cleanup dbPlugin
        try:
            db_plugin = PluginManager().dbPlugin
            if db_plugin:
                await db_plugin.cleanup()
        except Exception as e:
            logger.warning(f"Error during dbPlugin cleanup: {e}")

        logger.info("Application shutdown")

        # cleanup global vars and thread local storage
        try:
            cleanup_global_vars()
        except Exception as e:
            print(f"Error during global vars cleanup: {e}")

        # cleanup logging last to ensure all logs are written
        try:
            cleanup_logging("whisker")
        except Exception as e:
            print(f"Error during logging cleanup: {e}")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        # Still try to cleanup resources even if other cleanup fails
        try:
            cleanup_global_vars()
        except Exception as cleanup_error:
            print(
                f"Error during global vars cleanup after shutdown error: {cleanup_error}"
            )

        try:
            cleanup_logging("whisker")
        except Exception as cleanup_error:
            print(f"Error during logging cleanup after shutdown error: {cleanup_error}")


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    await startup_event()
    try:
        yield
    finally:
        await shutdown_event()


def create_app() -> FastAPI:
    """create and configure FastAPI application"""

    # init log and base settings
    log_dir = os.getenv("LOG_DIR", "/tmp/logs")
    setup_logging("whisker", log_dir)

    # inject global vars

    inject_global_vars()
    logger.info("Global variables injected into builtins")

    # init register
    init_register("whiskerrag_utils")

    # create FastAPI application
    app = FastAPI(lifespan=lifespan, title="whisker rag server", version="1.0.6")

    # add exception handling middleware FIRST (before plugins)
    @app.middleware("http")
    async def exception_handling_middleware(request: Request, call_next):
        """Middleware to handle exceptions and create responses that go through the full middleware stack"""
        start_time = time.time()

        try:
            response = await call_next(request)

            # Add process time header to all responses
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = f"{process_time:.4f}"

            return response

        except HTTPException as exc:
            # Create error response for HTTP exceptions
            error_message = str(exc.detail) if isinstance(exc.detail, str) else str(exc)

            logger.error(
                f"HTTPException in middleware: "
                f"Path={request.url.path}, Method={request.method}, "
                f"Status Code={exc.status_code}, Message={error_message}, "
                f"Traceback={traceback.format_exc()}"
            )

            response_content = ResponseModel(
                success=False, message=error_message, data=None
            ).model_dump()

            response = JSONResponse(
                status_code=exc.status_code, content=response_content
            )

            # Add process time header to error response
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = f"{process_time:.4f}"

            return response

        except Exception as exc:
            # Create error response for general exceptions
            exc_info = sys.exc_info()
            logger.error(
                f"General exception in middleware: Path={request.url.path}, Method={request.method}",
                exc_info=exc_info,
            )

            response_content = ResponseModel(
                success=False, message=f"Internal Server Error: {exc}", data=None
            ).model_dump()

            response = JSONResponse(status_code=500, content=response_content)

            # Add process time header to error response
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = f"{process_time:.4f}"

            return response

    # let plugin manager setup application (including middleware)
    plugin_abs_path = resolve_plugin_path()
    logger.info(f"plugin_abs_path: {plugin_abs_path}")
    plugin_manager = PluginManager(plugin_abs_path)
    plugin_manager.setup_plugins(app)

    # Simplified exception handlers (these will rarely be called now)
    @app.exception_handler(404)
    async def http404_error_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=404,
            content=ResponseModel(
                success=False, message=exc.detail, data=None
            ).model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        error_message = str(exc.detail) if isinstance(exc.detail, str) else str(exc)

        logger.error(
            f"HTTPException in fallback handler: "
            f"Path={request.url.path}, Method={request.method}, "
            f"Status Code={exc.status_code}, Message={error_message}"
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=ResponseModel(
                success=False, message=error_message, data=None
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        exc_info = sys.exc_info()
        logger.error(
            f"General exception in fallback handler: Path={request.url.path}, Method={request.method}",
            exc_info=exc_info,
        )

        return JSONResponse(
            status_code=500,
            content=ResponseModel(
                success=False, message=f"Internal Server Error: {exc}", data=None
            ).model_dump(),
        )

    # add CORS middleware
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

    # include routers
    app.include_router(knowledge_router.router)
    app.include_router(retrieval_router.router)
    app.include_router(task_router.router)
    app.include_router(chunk_router.router)
    app.include_router(tenant_router.router)
    app.include_router(space_router.router)
    app.include_router(rule_router.router)
    app.include_router(api_key_router.router)
    app.include_router(agent_router.router)

    # add base router
    @app.get("/")
    def home_page() -> RedirectResponse:
        return RedirectResponse(url=settings.WEB_URL)

    @app.get("/api/health_checker", response_model=ResponseModel)
    def health_checker() -> ResponseModel[dict]:
        res = {"env": os.getenv("WHISKER_ENV"), "extra": "hello"}
        logger.debug(f"health check: {res}")
        return ResponseModel(success=True, data=res)

    return app


# create application instance
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
