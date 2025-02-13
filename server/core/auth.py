from typing import Callable

from fastapi import Header, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from whiskerrag_types.model import Tenant

from .plugin_manager import PluginManager


async def verify_api_key(auth_str: str) -> bool:
    tenant_sk = get_sk_from_header(auth_str)
    db = PluginManager().dbPlugin
    validate_res = db.validate_tenant_by_sk(tenant_sk)
    if not validate_res:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return True


def require_auth() -> Callable:
    def decorator(func: Callable) -> Callable:
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


def get_sk_from_header(header_auth: str) -> str:
    api_key: str = header_auth.split(" ")[1]
    return api_key


async def get_tenant(header_auth: str = Header(None, alias="Authorization")) -> Tenant:
    if not header_auth:
        raise HTTPException(status_code=401, detail="API Key is missing")
    db = PluginManager().dbPlugin
    tenant = await db.get_tenant_by_sk(get_sk_from_header(header_auth))
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return tenant
