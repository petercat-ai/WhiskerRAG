import json
import os
import time
from typing import Any, Dict, List, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from whiskerrag_types.interface import FastAPIPluginInterface
from core.log import logger


class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        is_dev_env = os.getenv("WHISKER_ENV", "dev") == "dev"

        start_time = time.time()

        body = b""
        if request.method in ["POST", "PUT", "PATCH"] and is_dev_env:
            try:
                body = await request.body()

                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive
            except Exception as e:
                logger.warning(f"Failed to read request body: {e}")

        if is_dev_env:
            logger.info("=" * 50)
            logger.info(f"📥 REQUEST: {request.method} {request.url}")
            logger.info(
                f"🌐 Client IP: {request.client.host if request.client else 'unknown'}"
            )
            logger.info(f"📋 Headers: {dict(request.headers)}")

            if request.query_params:
                logger.info(f"🔍 Query Params: {dict(request.query_params)}")

            if body:
                try:
                    content_type = request.headers.get("content-type", "")
                    if "application/json" in content_type:
                        body_json = json.loads(body.decode("utf-8"))
                        logger.info(
                            f"📦 Request Body (JSON): {json.dumps(body_json, indent=2, ensure_ascii=False)}"
                        )
                    else:
                        body_str = body.decode("utf-8", errors="ignore")
                        if len(body_str) > 200:
                            body_str = body_str[:200] + "..."
                        logger.info(f"📦 Request Body: {body_str}")
                except Exception as e:
                    logger.info(
                        f"📦 Request Body (raw, {len(body)} bytes): {body[:100]}..."
                    )

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            if is_dev_env:
                response_body = b""
                if isinstance(response, StreamingResponse):
                    logger.info(
                        f"📤 RESPONSE: Status {response.status_code} (Streaming Response)"
                    )
                else:
                    if hasattr(response, "body"):
                        response_body = response.body
                    else:
                        try:
                            response_body = b"".join(
                                [chunk async for chunk in response.body_iterator]
                            )
                            response = Response(
                                content=response_body,
                                status_code=response.status_code,
                                headers=dict(response.headers),
                                media_type=response.media_type,
                            )
                        except Exception as e:
                            logger.warning(f"Failed to read response body: {e}")

                    logger.info(f"📤 RESPONSE: Status {response.status_code}")
                    logger.info(f"⏱️  Process Time: {process_time:.4f}s")
                    logger.info(f"📋 Response Headers: {dict(response.headers)}")

                    if response_body:
                        try:
                            content_type = response.headers.get("content-type", "")
                            if "application/json" in content_type:
                                response_json = json.loads(
                                    response_body.decode("utf-8")
                                )
                                logger.info(
                                    f"📦 Response Body (JSON): {json.dumps(response_json, indent=2, ensure_ascii=False)}"
                                )
                            else:
                                response_str = response_body.decode(
                                    "utf-8", errors="ignore"
                                )
                                if len(response_str) > 500:
                                    response_str = response_str[:500] + "..."
                                logger.info(f"📦 Response Body: {response_str}")
                        except Exception as e:
                            logger.info(
                                f"📦 Response Body (raw, {len(response_body)} bytes): {response_body[:200]}..."
                            )

                logger.info("=" * 50)
            else:
                # 生产环境只记录基本信息，不包含敏感数据
                logger.info(
                    f"REQUEST: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s"
                )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            if is_dev_env:
                logger.error(f"❌ REQUEST FAILED: {request.method} {request.url}")
                logger.error(f"⏱️  Process Time: {process_time:.4f}s")
                logger.error(f"💥 Error: {str(e)}")
                logger.info("=" * 50)
            else:
                # 生产环境只记录错误的基本信息
                logger.error(
                    f"REQUEST FAILED: {request.method} {request.url.path} - Time: {process_time:.4f}s - Error: {type(e).__name__}"
                )
            raise


class FastAPIPlugin(FastAPIPluginInterface):
    def get_extra_middleware_list(self) -> List[Tuple[Any, Dict[str, Any]]]:
        return [(RequestResponseLoggingMiddleware, {})]
