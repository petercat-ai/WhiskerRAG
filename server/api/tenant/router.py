import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import secrets
from whiskerrag_types.model import Tenant

from core.auth import get_tenant
from core.response import ResponseModel
from core.plugin_manager import PluginManager


router = APIRouter(
    prefix="/api/tenant",
    tags=["tenant"],
    responses={404: {"description": "Not found"}},
)


class TenantCreate(BaseModel):
    tenant_name: str
    email: Optional[str] = None


@router.post("/create", operation_id="create_tenant", response_model_by_alias=False)
async def create_tenant(params: TenantCreate) -> ResponseModel[Tenant]:
    api_secret_key = f"sk-{secrets.token_urlsafe(32)}"
    # api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    db_engine = PluginManager().dbPlugin
    if not await db_engine.validate_tenant_name(params.tenant_name):
        raise HTTPException(
            status_code=400, detail=f"Tenant {params.tenant_name} already exists!"
        )
    tenant = await db_engine.save_tenant(
        Tenant(
            tenant_id=str(uuid.uuid4()),
            tenant_name=params.tenant_name,
            email=params.email,
            secret_key=api_secret_key,
            is_active=True,
        )
    )
    return ResponseModel(data=tenant, success=True)


@router.get("/me", operation_id="get_tenant", response_model_by_alias=False)
async def get_tenant(tenant: Tenant = Depends(get_tenant)):
    return tenant
