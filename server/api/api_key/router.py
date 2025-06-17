import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import iso8601
from core.auth import Action, Resource, get_tenant_with_permissions
from core.log import logger
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from whiskerrag_types.model import (
    APIKey,
    PageQueryParams,
    PageResponse,
    Permission,
    Tenant,
)


class APIKeyCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key_name: str = Field(default="")
    description: Optional[str] = None
    permissions: List[Permission] = Field(default_factory=list)
    rate_limit: Optional[int] = Field(default=0, ge=0)
    expires_at: Optional[str] = Field(
        default=None,
        description="Expiration time in ISO8601 format with timezone (e.g., 2024-12-31T23:59:59+00:00)",
    )
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("expires_at")
    def validate_expires_at(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        try:
            dt = iso8601.parse_date(v)
            if dt.tzinfo is None:
                raise ValueError("Timezone information is required")

            now = datetime.now(timezone.utc)
            if dt < now:
                raise ValueError("expires_at must be future time")

            return dt

        except ValueError as e:
            raise ValueError(
                "Invalid expires_at format. Must be ISO8601 format with timezone "
                "(e.g., 2025-12-31T23:59:59+00:00)"
            )


class APIKeyUpdate(APIKeyCreate):
    model_config = ConfigDict(str_strip_whitespace=True)

    key_id: str


class ActiveStatusUpdate(BaseModel):
    key_id: str
    status: bool


router = APIRouter(
    prefix="/api/api_key",
    tags=["api key"],
    responses={404: {"description": "Not found"}},
)


@router.post("/create", operation_id="create_api_key", response_model_by_alias=False)
async def create_api_key(
    body: APIKeyCreate,
    tenant: Tenant = get_tenant_with_permissions(Resource.API_KEY, [Action.CREATE]),
) -> ResponseModel[APIKey]:
    api_secret_key = f"ak-{secrets.token_urlsafe(32)}"
    db_engine = PluginManager().dbPlugin
    api_key = APIKey(
        **body.model_dump(exclude_unset=True, exclude_none=True),
        tenant_id=tenant.tenant_id,
        key_value=api_secret_key,
    )
    new_api_key = await db_engine.save_api_key(api_key)
    return ResponseModel(data=new_api_key, success=True)


@router.post("/update", operation_id="update_api_key", response_model_by_alias=False)
async def update_api_key(
    body: APIKeyUpdate,
    tenant: Tenant = get_tenant_with_permissions(Resource.API_KEY, [Action.UPDATE]),
) -> ResponseModel[APIKey]:
    db_engine = PluginManager().dbPlugin
    existing_key = await db_engine.get_api_key_by_id(tenant.tenant_id, body.key_id)
    if not existing_key:
        raise HTTPException(
            status_code=404,
            detail=f"API Key id : {body.key_id} not found or does not belong to the tenant",
        )
    # Merge fields from existing_key and body to create a full update object
    update_data = existing_key.model_dump()
    update_data.update(body.model_dump(exclude_unset=True, exclude_none=True))
    update_data["tenant_id"] = tenant.tenant_id
    updated_api_key = await db_engine.update_api_key(APIKey(**update_data))
    return ResponseModel(data=updated_api_key, success=True)


@router.post("/list", operation_id="get_api_key_list", response_model_by_alias=False)
async def get_api_key_list(
    body: PageQueryParams[APIKey],
    tenant: Tenant = get_tenant_with_permissions(Resource.API_KEY, [Action.READ]),
) -> ResponseModel[PageResponse[APIKey]]:
    db_engine = PluginManager().dbPlugin
    api_keys = await db_engine.get_tenant_api_keys(tenant.tenant_id, body)
    return ResponseModel(data=api_keys, success=True)


@router.delete(
    "/delete/{key_id}", operation_id="delete_api_key", response_model_by_alias=False
)
async def delete_api_key(
    key_id: str,
    tenant: Tenant = get_tenant_with_permissions(Resource.API_KEY, [Action.DELETE]),
) -> ResponseModel[None]:
    logger.info("[delete_api_key][start], key_id=%s", key_id)
    try:
        db_engine = PluginManager().dbPlugin
        existing_key = await db_engine.get_api_key_by_id(tenant.tenant_id, key_id)
        if not existing_key or existing_key.tenant_id != tenant.tenant_id:
            raise HTTPException(status_code=404, detail="API Key not found")

        success = await db_engine.delete_api_key(key_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete API key")

        return ResponseModel(success=True, message="API key deleted successfully")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("[delete_api_key][error], key_id=%s, error=%s", key_id, str(e))
        raise


@router.post(
    "/deactivate/{key_id}",
    operation_id="deactivate_api_key",
    response_model_by_alias=False,
)
async def change_api_key_status(
    body: ActiveStatusUpdate,
    tenant: Tenant = get_tenant_with_permissions(Resource.API_KEY, [Action.UPDATE]),
) -> ResponseModel[None]:
    db_engine = PluginManager().dbPlugin
    existing_key = await db_engine.get_api_key_by_id(tenant.tenant_id, body.key_id)
    if not existing_key or existing_key.tenant_id != tenant.tenant_id:
        raise HTTPException(status_code=404, detail="API Key not found")
    existing_key.is_active = body.status
    await db_engine.update_api_key(existing_key)
    return ResponseModel(success=True, message="API key deactivated successfully")


@router.get(
    "/expired", operation_id="get_all_expired_api_keys", response_model_by_alias=False
)
async def get_all_expired_api_keys(
    tenant: Tenant = get_tenant_with_permissions(Resource.API_KEY, [Action.READ]),
) -> ResponseModel[List[APIKey]]:
    db_engine = PluginManager().dbPlugin
    expired_keys = await db_engine.get_all_expired_api_keys(tenant.tenant_id)
    return ResponseModel(data=expired_keys, success=True)
