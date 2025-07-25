import logging
from datetime import datetime, timezone
from typing import Callable, List, Optional, Tuple

from fastapi import Depends, Header, HTTPException, Request
from whiskerrag_types.model import Action, APIKey, Resource, Tenant

from .cache import TTLCache
from .plugin_manager import PluginManager

AuthResult = Tuple[bool, Optional[Tenant], Optional[APIKey], Optional[str]]

logger = logging.getLogger("whisker")


def extract_key(auth_header: str) -> str:
    parts = auth_header.strip().split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401, detail="Authorization header must start with 'Bearer'"
        )
    return parts[1]


def is_api_key_format(auth_str: str) -> bool:
    try:
        key = extract_key(auth_str)
        return key.startswith("ak-")
    except:
        return False


@TTLCache(ttl=60, maxsize=1000)
async def authenticate_ak(auth_header: str) -> AuthResult:
    api_key_str = extract_key(auth_header)
    db = PluginManager().dbPlugin
    api_key = await db.get_api_key_by_value(api_key_str)
    if not api_key:
        return False, None, None, "Invalid API key"
    tenant_id = api_key.tenant_id
    tenant = await db.get_tenant_by_id(tenant_id)
    if not tenant:
        return False, None, api_key, "Invalid API key"

    return True, tenant, api_key, None


@TTLCache(ttl=300, maxsize=1000)
async def authenticate_sk(auth_header: str) -> AuthResult:
    sk = extract_key(auth_header)
    db = PluginManager().dbPlugin
    tenant = await db.get_tenant_by_sk(sk)
    if not tenant:
        return False, None, None, "Invalid SK"

    return True, tenant, None, None


def check_api_key_validity(api_key: APIKey) -> bool:
    if not api_key.is_active:
        return False

    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        return False

    return True


def check_resource_permissions(
    api_key: APIKey, resource: Resource, actions: List[Action]
) -> bool:

    for permission in api_key.permissions:
        if permission.resource == resource:
            if Action.ALL in permission.actions:
                return True
            return all(action in permission.actions for action in actions)
    return False


async def verify_permissions(
    api_key: APIKey, resource: Resource, actions: List[Action]
) -> bool:
    if resource == Resource.PUBLIC:
        return True

    if not hasattr(api_key, "key_value"):
        return False

    if not check_api_key_validity(api_key):
        return False

    return check_resource_permissions(api_key, resource, actions)


def set_tenant_id(tenant_id: str):
    """set tenant_id to global context"""
    try:
        if isinstance(__builtins__, dict):
            tenant_context = __builtins__.get("tenant_context")
        else:
            tenant_context = getattr(__builtins__, "tenant_context", None)

        if tenant_context:
            # set ContextVar (for async context passing)
            tenant_context.set(tenant_id)

            # set thread local storage as fallback (for cross-thread passing)
            try:
                if isinstance(__builtins__, dict):
                    set_thread_tenant_id_func = __builtins__.get("set_thread_tenant_id")
                else:
                    set_thread_tenant_id_func = getattr(
                        __builtins__, "set_thread_tenant_id", None
                    )

                if set_thread_tenant_id_func:
                    set_thread_tenant_id_func(tenant_id)
            except Exception as e:
                logger.warning(f"Failed to set thread-local tenant_id: {e}")
        else:
            logger.error(
                "ERROR: tenant_context not found in builtins - global variables may not be injected"
            )
    except Exception as e:
        logger.error(f"ERROR: Failed to set tenant_id: {e}")

    return tenant_id


async def authenticate_request(
    request: Request,
    header_auth: str,
    resource: Resource = Resource.PUBLIC,
    actions: List[Action] = [],
) -> Tenant:
    if not header_auth:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    authenticate = (
        authenticate_ak if is_api_key_format(header_auth) else authenticate_sk
    )

    is_auth, tenant, api_key, error = await authenticate(header_auth)
    if not is_auth:
        raise HTTPException(status_code=403, detail=error)
    # check api key permissions
    if is_api_key_format(header_auth):
        if not await verify_permissions(api_key, resource, actions):
            raise HTTPException(status_code=403, detail="Permission denied")
    else:
        # not api key, so we assume it's a tenant secret key
        print(f"Access granted for resource: {resource}")

    # Set tenant context for logging
    set_tenant_id(tenant.tenant_id)

    return tenant


def get_tenant_with_permissions(resource: Resource, actions: List[Action]) -> Callable:
    async def dependency(
        request: Request,
        header_auth: Optional[str] = Header(None, alias="Authorization"),
    ):
        return await authenticate_request(request, header_auth, resource, actions)

    return Depends(dependency)


__all__ = [get_tenant_with_permissions, Resource, Action]
