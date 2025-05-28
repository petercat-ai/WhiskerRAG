import secrets
import uuid
from typing import Optional

from core.auth import get_tenant_with_permissions, Resource, Action
from core.log import logger
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from whiskerrag_types.model import PageQueryParams, PageResponse, Tenant

router = APIRouter(
    prefix="/api/tenant",
    tags=["tenant"],
    responses={404: {"description": "Not found"}},
)


class TenantCreate(BaseModel):
    tenant_name: str
    email: str
    metadata: Optional[dict] = None


class TenantUpdate(BaseModel):
    tenant_id: str
    tenant_name: Optional[str] = None
    email: Optional[str] = None
    metadata: Optional[dict] = None


@router.post("/create", operation_id="create_tenant", response_model_by_alias=False)
async def create_tenant(params: TenantCreate) -> ResponseModel[Tenant]:
    logger.info("[create_tenant][start],req={}".format(params))
    try:
        api_secret_key = f"sk-{secrets.token_urlsafe(32)}"
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
                metadata=params.metadata,
            )
        )
        logger.info("[create_tenant][end]")
        return ResponseModel(data=tenant, success=True)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[create_tenant][error], req={params}, error={str(e)}")
        raise HTTPException(status_code=500, detail="创建租户失败")


@router.get(
    "/id/{id}", operation_id="get_tenant_by_id", response_model=ResponseModel[Tenant]
)
async def query_tenant(
    id: str,
    tenant: Tenant = get_tenant_with_permissions(
        Resource.TENANT, [Action.READ, Action.UPDATE]
    ),
) -> ResponseModel[Tenant]:
    logger.info("[get_tenant_by_id][start],req={}".format(id))
    try:
        db_engine = PluginManager().dbPlugin
        tenant = await db_engine.get_tenant_by_id(id)

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        logger.info("[get_tenant_by_id][end]")
        return ResponseModel(data=tenant, success=True)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[get_tenant_by_id][error], req={id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="获取租户详情失败")


@router.delete(
    "/{id}",
    operation_id="delete_tenant_by_id",
)
async def delete_tenant(
    id: str,
    tenant: Tenant = get_tenant_with_permissions(Resource.TENANT, [Action.DELETE]),
) -> ResponseModel[object]:
    logger.info("[delete_tenant_by_id][start],req={}".format(id))
    try:
        db_engine = PluginManager().dbPlugin
        tenant = await db_engine.delete_tenant_by_id(id)

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        flag = True
        logger.info("[delete_tenant_by_id][end]")
        return ResponseModel(data=flag, success=True)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[delete_tenant_by_id][error], req={id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="删除租户失败")


@router.post("/update", operation_id="update_tenant")
async def update_tenant(
    params: TenantUpdate,
    tenant: Tenant = get_tenant_with_permissions(Resource.TENANT, [Action.UPDATE]),
) -> ResponseModel[Tenant]:
    logger.info("[update_tenant][start],req={}".format(params))
    try:
        api_secret_key = f"sk-{secrets.token_urlsafe(32)}"
        db_engine = PluginManager().dbPlugin
        if params.tenant_id != tenant.tenant_id:
            raise HTTPException(
                status_code=403,
                detail="Update Tenant error: please ensure that the tenant ID you are operating matches the tenant ID you belong to.",
            )
        tenant = await db_engine.update_tenant(
            Tenant(
                tenant_id=params.tenant_id,
                tenant_name=params.tenant_name,
                email=params.email,
                secret_key=api_secret_key,
                is_active=True,
                metadata=params.metadata,
            )
        )
        logger.info("[update_tenant][end]")
        return ResponseModel(data=tenant, success=True)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[update_tenant][error], req={params}, error={str(e)}")
        raise HTTPException(status_code=500, detail="更新租户失败")


@router.get(
    "/list",
    operation_id="get_tenant_list",
)
async def get_tenant_list(
    page: int = 1,
    page_size: int = 10,
    tenant: Tenant = get_tenant_with_permissions(
        Resource.TENANT, [Action.UPDATE, Action.READ]
    ),
) -> ResponseModel[PageResponse[Tenant]]:
    logger.info("[get_tenant_list][start]")
    try:
        db_engine = PluginManager().dbPlugin
        page_params = PageQueryParams(page=page, page_size=page_size)
        tenant_list: PageResponse[Tenant] = await db_engine.get_tenant_list(page_params)
        return ResponseModel(data=tenant_list, success=True)
    except Exception as e:
        logger.error(f"[get_tenant_list][error], error={str(e)}")
        raise HTTPException(status_code=500, detail="获取租户列表失败")


@router.get("/me", operation_id="get_tenant", response_model_by_alias=False)
async def get_tenant(
    tenant: Tenant = get_tenant_with_permissions(
        Resource.TENANT, [Action.UPDATE, Action.READ]
    ),
):
    logger.info("[get_tenant][start],req={}".format(tenant))
    return tenant
