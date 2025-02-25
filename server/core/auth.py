from fastapi import Header, HTTPException
from whiskerrag_types.model import Tenant

from .cache import TTLCache
from .plugin_manager import PluginManager


def get_sk_from_header(header_auth: str) -> str:
    api_key: str = header_auth.split(" ")[1]
    return api_key


@TTLCache(ttl=300, maxsize=1000)
async def get_tenant_by_heder_auth(auth_str: str) -> Tenant | None:
    sk = get_sk_from_header(auth_str)
    db = PluginManager().dbPlugin
    res = await db.get_tenant_by_sk(sk)
    return res


async def get_tenant(header_auth: str = Header(None, alias="Authorization")) -> Tenant:
    if not header_auth:
        raise HTTPException(status_code=401, detail="API Key is missing")
    tenant = await get_tenant_by_heder_auth(header_auth)
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return tenant
