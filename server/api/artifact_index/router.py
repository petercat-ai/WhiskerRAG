from typing import Annotated, List
from fastapi import APIRouter, Body, HTTPException, Path
from pydantic import BaseModel
from whiskerrag_types.model import (
    PageQueryParams,
    PageResponse,
    Tenant,
)
from whiskerrag_types.model.artifact_index import ArtifactIndexCreate, ArtifactIndex
from core.auth import Action, Resource, get_tenant_with_permissions
from core.log import logger
from core.plugin_manager import PluginManager
from core.response import ResponseModel
from whiskerrag_types.interface import DBPluginInterface

router = APIRouter(
    prefix="/api/v1/artifact",
    tags=["artifact"],
    responses={404: {"description": "Not found"}},
)


async def get_db_engine() -> DBPluginInterface:
    db_engine = PluginManager().dbPlugin
    if db_engine is None:
        raise HTTPException(status_code=500, detail="DB plugin is not initialized")
    await db_engine.ensure_initialized()
    return db_engine


@router.post("/list", operation_id="get_artifact_list", response_model_by_alias=False)
async def get_artifact_list(
    body: PageQueryParams[ArtifactIndex],
    tenant: Annotated[
        Tenant, get_tenant_with_permissions(Resource.ARTIFACT, [Action.READ])
    ],
) -> ResponseModel[PageResponse[ArtifactIndex]]:
    db_engine = await get_db_engine()
    artifact_list = await db_engine.get_artifact_list(body)
    return ResponseModel(data=artifact_list, success=True)


@router.post(
    "/add_list", operation_id="add_artifact_list", response_model_by_alias=False
)
async def add_artifact_list(
    body: List[ArtifactIndexCreate],
    tenant: Annotated[
        Tenant, get_tenant_with_permissions(Resource.ARTIFACT, [Action.CREATE])
    ],
) -> ResponseModel[List[ArtifactIndex]]:
    db_engine = await get_db_engine()
    created_arts = await db_engine.add_artifact_list(body)
    return ResponseModel(data=created_arts, success=True)


@router.get(
    "/{artifact_id}", operation_id="get_artifact_by_id", response_model_by_alias=False
)
async def get_artifact_by_id(
    tenant: Annotated[
        Tenant, get_tenant_with_permissions(Resource.ARTIFACT, [Action.READ])
    ],
    artifact_id: str = Path(..., description="artifact id"),
) -> ResponseModel[ArtifactIndex]:
    db_engine = await get_db_engine()
    artifact = await db_engine.get_artifact_by_id(artifact_id)
    if not artifact:
        logger.warning(
            "[get_artifact_by_id][artifact not exists], artifact_id=%s", artifact_id
        )
        raise HTTPException(status_code=404, detail="artifact not exists")
    return ResponseModel(data=artifact, success=True)


@router.delete(
    "/{artifact_id}",
    operation_id="delete_artifact_by_id",
    response_model_by_alias=False,
)
async def delete_artifact_by_id(
    tenant: Annotated[
        Tenant, get_tenant_with_permissions(Resource.ARTIFACT, [Action.DELETE])
    ],
    artifact_id: str = Path(..., description="artifact id"),
) -> ResponseModel[None]:
    db_engine = await get_db_engine()
    deleted = await db_engine.delete_artifact_by_id(artifact_id)
    if not deleted:
        logger.warning(
            "[delete_artifact_by_id][artifact not exists], artifact_id=%s", artifact_id
        )
        raise HTTPException(status_code=404, detail="artifact not exists")
    return ResponseModel(
        success=True, message=f"Artifact {artifact_id} deleted successfully"
    )


class ArtifactSpaceUpdate(BaseModel):
    artifact_id: str
    new_space_id: str


@router.post(
    "/update_space",
    operation_id="update_artifact_space_id",
    response_model_by_alias=False,
)
async def update_artifact_space_id(
    tenant: Annotated[
        Tenant, get_tenant_with_permissions(Resource.ARTIFACT, [Action.UPDATE])
    ],
    body: ArtifactSpaceUpdate = Body(..., description="要更新的 artifact 空间绑定"),
) -> ResponseModel[ArtifactIndex]:
    db_engine = await get_db_engine()
    if not body.artifact_id:
        raise HTTPException(status_code=400, detail="artifact_id is required")

    exist = await db_engine.get_artifact_by_id(body.artifact_id)
    if not exist:
        logger.error(
            "[update_artifact_space_id][artifact不存在], artifact_id=%s",
            body.artifact_id,
        )
        raise HTTPException(
            status_code=404, detail=f"artifact不存在,artifact_id={body.artifact_id}"
        )

    updated_artifact = await db_engine.update_artifact_space_id(
        body.artifact_id, body.new_space_id
    )
    return ResponseModel(
        success=True, data=updated_artifact, message="Update artifact succeed"
    )
