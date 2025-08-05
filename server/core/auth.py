import logging
from fastapi import Header, HTTPException
from whiskerrag_types.model import Tenant, APIKey, Resource, Action
from typing import Optional, List, Callable, Tuple
from fastapi import Depends, HTTPException, Request
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
        if not header_auth:
            raise HTTPException(
                status_code=401,
                detail="Authorization header is missing. Please include a valid API key or secret key.",
            )
        return await authenticate_request(request, header_auth, resource, actions)

    return Depends(dependency)


async def authenticate_by_key_string(
    key_string: str,
    resource: Resource = Resource.PUBLIC,
    actions: List[Action] = [],
) -> Tenant:
    """
    根据 ak 或 sk 字符串进行鉴权

    Args:
        key_string: API key 或 Secret key 字符串 (以 ak- 或 sk- 开头)
        resource: 需要访问的资源
        actions: 需要执行的操作列表

    Returns:
        Tenant: 验证通过的租户对象

    Raises:
        HTTPException: 鉴权失败时抛出异常
    """
    if not key_string:
        raise HTTPException(status_code=401, detail="Key string is missing")

    # 验证 key 格式
    if not (key_string.startswith("ak-") or key_string.startswith("sk-")):
        raise HTTPException(
            status_code=401, detail="Key must start with 'ak-' or 'sk-'"
        )

    # 构造 Authorization header 格式进行复用现有逻辑
    auth_header = f"Bearer {key_string}"

    # 根据 key 类型选择认证方法
    authenticate = authenticate_ak if key_string.startswith("ak-") else authenticate_sk

    is_auth, tenant, api_key, error = await authenticate(auth_header)
    if not is_auth:
        raise HTTPException(status_code=403, detail=error)

    # 检查 API key 权限
    if key_string.startswith("ak-"):
        if not await verify_permissions(api_key, resource, actions):
            raise HTTPException(status_code=403, detail="Permission denied")
    else:
        # SK 情况下，记录访问日志
        logger.info(f"Access granted for resource: {resource} with SK")

    # 设置租户上下文
    set_tenant_id(tenant.tenant_id)

    return tenant


async def authenticate_multiple_keys(
    keys: List[str],
    resource: Resource = Resource.PUBLIC,
    actions: List[Action] = [],
) -> List[Tuple[str, Optional[Tenant], Optional[str]]]:
    """
    批量验证多个 key

    Args:
        keys: key 字符串列表
        resource: 需要访问的资源
        actions: 需要执行的操作列表

    Returns:
        List[Tuple[str, Optional[Tenant], Optional[str]]]:
        每个元素为 (key, tenant_or_none, error_message_or_none)
    """
    results = []

    for key in keys:
        try:
            tenant = await authenticate_by_key_string(key, resource, actions)
            results.append((key, tenant, None))
        except HTTPException as e:
            results.append((key, None, e.detail))
        except Exception as e:
            results.append((key, None, str(e)))

    return results


async def validate_key_string(
    key_string: str,
    resource: Resource = Resource.PUBLIC,
    actions: List[Action] = [],
) -> Tuple[bool, Optional[Tenant], Optional[str]]:
    """
    验证 key 字符串是否有效（不抛出异常的版本）

    Args:
        key_string: API key 或 Secret key 字符串
        resource: 需要访问的资源
        actions: 需要执行的操作列表

    Returns:
        Tuple[bool, Optional[Tenant], Optional[str]]:
        (是否验证成功, 租户对象或None, 错误信息或None)
    """
    try:
        tenant = await authenticate_by_key_string(key_string, resource, actions)
        return True, tenant, None
    except HTTPException as e:
        return False, None, e.detail
    except Exception as e:
        return False, None, str(e)


__all__ = [
    get_tenant_with_permissions,
    authenticate_multiple_keys,
    validate_key_string,
    Action,
]
