from core.auth import get_tenant
from core.log import logger
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from whiskerrag_types.model import (
    PageParams,
    PageResponse,
    Space,
    SpaceCreate,
    SpaceResponse,
    Tenant,
)

router = APIRouter(
    prefix="/api/space",
    tags=["space"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_tenant)],
)


@router.post(
    "/list",
    operation_id="get_space_list",
    response_model_by_alias=False,
)
async def get_space_list(
    body: PageParams[Space],
    tenant: Tenant = Depends(get_tenant),
) -> ResponseModel[PageResponse[SpaceResponse]]:
    """获取知识库分页列表"""
    logger.info(f"[get_space_list][start], req={body}")
    try:
        db_engine = PluginManager().dbPlugin
        space_list: PageResponse[SpaceResponse] = await db_engine.get_space_list(
            tenant.tenant_id, body
        )
        return ResponseModel(data=space_list, success=True)
    except Exception as e:
        logger.error(f"[get_space_list][error], req={body}, error={str(e)}")
        raise HTTPException(status_code=500, detail="获取知识库列表失败")


@router.post("/add", operation_id="add_space", response_model_by_alias=False)
async def add_space(
    body: SpaceCreate,
    tenant: Tenant = Depends(get_tenant),
) -> ResponseModel[SpaceResponse]:
    """创建知识库"""
    logger.info(f"[add_space][start], req={body}")
    try:
        db_engine = PluginManager().dbPlugin
        # 自动填充 tenant_id 和 space_id（通过 DAO 的 save 方法）
        created_space = await db_engine.save_space(
            Space(**body.model_dump(), tenant_id=tenant.tenant_id)
        )
        return ResponseModel(data=created_space, success=True)
    except Exception as e:
        logger.error(f"[add_space][error], req={body}, error={str(e)}")
        raise HTTPException(status_code=500, detail="创建知识库失败")


@router.delete(
    "/{space_id}",
    operation_id="delete_space",
    response_model_by_alias=False,
)
async def delete_space(
    space_id: str = Path(..., description="知识库ID"),
    tenant: Tenant = Depends(get_tenant),
) -> ResponseModel[None]:
    """删除知识库"""
    logger.info(f"[delete_space][start], req={space_id}")
    try:
        db_engine = PluginManager().dbPlugin
        space = await db_engine.get_space(tenant.tenant_id, space_id)
        if not space:
            logger.error("[delete_space][知识库不存在],space_id={}".format(space_id))
            raise HTTPException(
                status_code=404, detail=f"知识库不存在, space_id={space_id}"
            )
        await db_engine.delete_space(tenant.tenant_id, space_id)
        return ResponseModel(
            success=True, message=f"Space {space_id} deleted successfully"
        )
    except HTTPException as e:
        # 保留原有的 HTTPException（如 404）
        raise e
    except Exception as e:
        logger.error(f"[delete_space][error], req={space_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="删除知识库失败")


@router.put("/{space_id}", operation_id="update_space", response_model_by_alias=False)
async def update_space(
    space_id: str = Path(..., description="知识库唯一标识符"),
    body: SpaceCreate = Body(..., description="更新后的知识库信息"),
    tenant: Tenant = Depends(get_tenant),
) -> ResponseModel[SpaceResponse]:
    """修改知识库信息,注意:tenant_id 和 space_id 字段不可修改"""
    logger.info(f"[update_space][start], req={space_id}")
    try:
        db_engine = PluginManager().dbPlugin
        # 1. 检查知识库是否存在
        existing_space = await db_engine.get_space(tenant.tenant_id, space_id)
        if not existing_space:
            logger.error("[update_space][知识库不存在],space_id={}".format(space_id))
            raise HTTPException(
                status_code=404, detail=f"知识库不存在, space_id={space_id}"
            )
        # 2. 执行更新
        updated_space = await db_engine.update_space(
            Space(**body.model_dump(), space_id=space_id, tenant_id=tenant.tenant_id)
        )
        return ResponseModel(data=updated_space, success=True, message="知识库更新成功")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[update_space][error], req={space_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="更新知识库失败")


@router.get(
    "/{space_id}", operation_id="get_space_by_id", response_model_by_alias=False
)
async def get_space_by_id(
    space_id: str = Path(..., description="知识库唯一标识符"),
    tenant: Tenant = Depends(get_tenant),
) -> ResponseModel[SpaceResponse]:
    """获取知识库详情"""
    logger.info(f"[get_space_by_id][start], req={space_id}")
    try:
        db_engine = PluginManager().dbPlugin
        space = await db_engine.get_space(tenant.tenant_id, space_id)
        if not space:
            logger.error("[get_space_by_id][知识库不存在],space_id={}".format(space_id))
            raise HTTPException(status_code=404, detail="知识库不存在")
        return ResponseModel(data=space, success=True)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"[get_space_by_id][error], req={space_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="获取知识库详情失败")
