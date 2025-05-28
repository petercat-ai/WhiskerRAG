from fastapi import Header, HTTPException
from pydantic import BaseModel
from whiskerrag_types.model import Tenant, APIKey, Resource, Action
from typing import Optional, List, Callable, Tuple
from fastapi import Depends, HTTPException, Request
from datetime import datetime, timezone
from .plugin_manager import PluginManager
from .cache import TTLCache

AuthResult = Tuple[bool, Optional[Tenant], Optional[APIKey], Optional[str]]


async def get_from_cache(key: str) -> Optional[any]:
    data = await cache.get(key)
    if data and isinstance(data, dict):
        return Tenant(**data)
    return data


async def set_to_cache(key: str, value: any) -> None:
    if isinstance(value, BaseModel):
        value = value.model_dump()
    await cache.set(key, value)


def extract_key(auth_header: str) -> str:
    return auth_header.split(" ")[1]


def is_api_key_format(auth_str: str) -> bool:
    try:
        key = extract_key(auth_str)
        return key.startswith("ak-")
    except:
        return False


@TTLCache(ttl=60, maxsize=1000)
async def authenticate_api_key(auth_header: str) -> AuthResult:
    api_key_str = extract_key(auth_header)
    db = PluginManager().dbPlugin
    api_key = await db.get_api_key_by_value(api_key_str)
    if not api_key:
        return False, None, "Invalid API key"
    tenant_id = api_key.tenant_id
    tenant = await db.get_tenant_by_id(tenant_id)
    if not tenant:
        return False, None, "Tenant not found for the API key"

    if not tenant:
        return False, None, "Invalid API key"

    return True, tenant, api_key, None


@TTLCache(ttl=300, maxsize=1000)
async def authenticate_sk(auth_header: str) -> AuthResult:
    sk = extract_key(auth_header)

    tenant = await get_from_cache(sk)
    if not tenant:
        db = PluginManager().dbPlugin
        tenant = await db.get_tenant_by_sk(sk)
        if tenant:
            await set_to_cache(sk, tenant)

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


async def authenticate_request(
    request: Request,
    header_auth: str,
    resource: Resource = Resource.PUBLIC,
    actions: List[Action] = None,
) -> Tenant:
    if not header_auth:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    authenticate = (
        authenticate_api_key if is_api_key_format(header_auth) else authenticate_sk
    )

    is_auth, tenant, api_key, error = await authenticate(header_auth)
    if not is_auth:
        raise HTTPException(status_code=401, detail=error)

    if actions and is_api_key_format(header_auth):
        if not await verify_permissions(api_key, resource, actions):
            raise HTTPException(status_code=403, detail="Permission denied")

    return tenant


def get_tenant_with_permissions(resource: Resource, actions: List[Action]) -> Callable:
    async def dependency(
        request: Request,
        header_auth: Optional[str] = Header(None, alias="Authorization"),
    ):
        return await authenticate_request(request, header_auth, resource, actions)

    return Depends(dependency)


__all__ = [get_tenant_with_permissions, Resource, Action]
