from typing import Callable
from fastapi import HTTPException, Header, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from .log import logger
from .plugin_manager import PluginManager
from whiskerrag_types.model import Tenant


async def verify_api_key(auth_str: str):
    tenant_sk = get_sk_from_header(auth_str)
    db = PluginManager().dbPlugin
    validate_res = db.validate_tenant_by_sk(tenant_sk)
    if not validate_res:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return True


def require_auth():
    def decorator(func: Callable):
        setattr(func, "require_auth", True)
        return func

    return decorator


class TenantAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        route_handler = None
        if request.scope.get("endpoint"):
            route_handler = request.scope["endpoint"]

        if route_handler and getattr(route_handler, "require_auth", False):
            header_auth = request.headers.get("Authorization")
            if not header_auth:
                raise HTTPException(status_code=401, detail="API Key is missing")

            await verify_api_key(header_auth)

        response = await call_next(request)
        return response


def get_sk_from_header(header_auth):
    api_key = header_auth.split(" ")[1]
    return api_key


# 定义依赖函数
async def get_tenant(header_auth: str = Header(None, alias="Authorization")) -> Tenant:
    if not header_auth:
        raise HTTPException(status_code=401, detail="API Key is missing")
    db = PluginManager().dbPlugin
    tenant = await db.get_tenant_by_sk(get_sk_from_header(header_auth))
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return tenant
