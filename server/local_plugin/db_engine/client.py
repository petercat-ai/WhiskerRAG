from enum import Enum
import json
from typing import Any, Dict, List, Optional, Type, TypeVar
import asyncpg
from fastapi import HTTPException, status
from pydantic import BaseModel
from whiskerrag_types.interface import DBPluginInterface
from whiskerrag_types.model import (
    Chunk,
    Knowledge,
    PageParams,
    PageResponse,
    RetrievalByKnowledgeRequest,
    RetrievalBySpaceRequest,
    RetrievalChunk,
    RetrievalRequest,
    Task,
    Tenant,
    KnowledgeSourceEnum,
    GenericConverter,
)
from whiskerrag_utils import RegisterTypeEnum, get_register
from pgvector.asyncpg import register_vector

T = TypeVar("T", bound=BaseModel)


class PostgresDBPlugin(DBPluginInterface):
    pool: Optional[asyncpg.Pool] = None

    def _prepare_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return json.dumps(value)
        return value

    async def _check_table_exists(self, pool: asyncpg.Pool, table_name: str) -> bool:
        try:
            async with pool.acquire() as conn:
                query = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    );
                """
                exists = await conn.fetchval(query, table_name)
                if exists:
                    self.logger.info(f"Table '{table_name}' connect success")
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Check table {table_name} error: {e}")
            return False

    def get_db_client(self) -> asyncpg.Pool:
        return self.pool

    async def init(self) -> None:
        try:
            POSTGRES_DB_HOST = self.settings.get_env("DB_HOST", "localhost")
            POSTGRES_DB_PORT = self.settings.get_env("DB_PORT", "5432")
            POSTGRES_DB_NAME = self.settings.get_env("DB_NAME", "whisker")
            POSTGRES_DB_USER = self.settings.get_env("DB_USER", "whisker")
            POSTGRES_DB_PASSWORD = self.settings.get_env("DB_PASSWORD", "whisker")
            if not all(
                [
                    POSTGRES_DB_HOST,
                    POSTGRES_DB_PORT,
                    POSTGRES_DB_NAME,
                    POSTGRES_DB_USER,
                    POSTGRES_DB_PASSWORD,
                ]
            ):
                raise Exception(
                    "Database configuration environment variables are missing"
                )

            self.pool = await asyncpg.create_pool(
                host=POSTGRES_DB_HOST,
                port=int(POSTGRES_DB_PORT),
                database=POSTGRES_DB_NAME,
                user=POSTGRES_DB_USER,
                password=POSTGRES_DB_PASSWORD,
                min_size=5,
                max_size=20,
                setup=register_vector,
            )

            # Ensure the pgvector extension is installed
            async with self.pool.acquire() as conn:
                try:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                except Exception as e:
                    self.logger.error(f"Failed to ensure vector extension: {e}")
                    raise

            required_tables = [
                self.settings.KNOWLEDGE_TABLE_NAME,
                self.settings.TASK_TABLE_NAME,
                self.settings.CHUNK_TABLE_NAME,
                self.settings.TENANT_TABLE_NAME,
            ]

            for table_name in required_tables:
                if not await self._check_table_exists(self.pool, table_name):
                    raise Exception(
                        f"Table {table_name} does not exist, please create the table first"
                    )

            self.converters: Dict[Type[BaseModel], GenericConverter] = {}
            self.knowledge_converter = self._get_converter(Knowledge)
            self.task_converter = self._get_converter(Task)
            self.chunk_converter = self._get_converter(Chunk)
            self.tenant_converter = self._get_converter(Tenant)
            self.retrievalChunk_converter = self._get_converter(RetrievalChunk)
            self.logger.info("PostgreSQL database connection initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            if self.pool:
                await self.pool.close()
            raise

    def _get_converter(self, model_class: Type[T]) -> GenericConverter[T]:
        if model_class not in self.converters:
            self.converters[model_class] = GenericConverter(model_class)
        return self.converters[model_class]

    async def cleanup(self) -> None:
        if self.pool:
            await self.pool.close()
            self.logger.info("Database connection pool closed")

    async def healthy(self) -> bool:
        """
        Check the health status of the database
        """
        try:
            if not self.pool:
                return False

            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False

    async def _get_paginated_data(
        self,
        tenant_id: str,
        table_name: str,
        model_class: T,
        page_params: PageParams,
    ) -> PageResponse[T]:
        try:
            params: List[any] = []
            param_index = 1

            query = f"SELECT * FROM {table_name}"
            count_query = f"SELECT COUNT(*) FROM {table_name}"

            where_conditions = []

            if page_params.eq_conditions:
                for field, value in page_params.eq_conditions.items():
                    if field == "tenant_id" and value != tenant_id:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Tenant {value} is not allowed to access this data.",
                        )

                    if isinstance(value, Enum):
                        value = value.value
                    elif isinstance(value, BaseModel):
                        value = json.dumps(value.model_dump())

                    where_conditions.append(f"{field} = ${param_index}")
                    params.append(value)
                    param_index += 1

            if where_conditions:
                where_clause = " WHERE " + " AND ".join(where_conditions)
                query += where_clause
                count_query += where_clause

            if page_params.order_by:
                order_fields = page_params.order_by.split(",")
                order_clauses = []

                for field in order_fields:
                    field = field.strip()
                    direction = (
                        "DESC"
                        if page_params.order_direction.lower() == "desc"
                        else "ASC"
                    )
                    order_clauses.append(f"{field} {direction}")

                query += f" ORDER BY {', '.join(order_clauses)}"

            query += f" LIMIT {page_params.limit} OFFSET {page_params.offset}"

            async with self.pool.acquire() as conn:
                total = await conn.fetchval(count_query, *params)

                rows = await conn.fetch(query, *params)
                converter = self._get_converter(model_class)
                items = [converter.from_db_dict(dict(row)) for row in rows]

                total_pages = (
                    total + page_params.page_size - 1
                ) // page_params.page_size

                return PageResponse[T](
                    items=items,
                    total=total,
                    page=page_params.page,
                    page_size=page_params.page_size,
                    total_pages=total_pages,
                )

        except HTTPException as http_ex:
            raise
        except Exception as e:
            self.logger.error(f"Error in _get_paginated_data: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}",
            )

    # =============== Knowledge ===============
    async def save_knowledge_list(
        self, knowledge_list: List[Knowledge]
    ) -> List[Knowledge]:
        async with self.pool.acquire() as conn:
            saved_knowledge = []
            for knowledge in knowledge_list:
                knowledge_dict = knowledge.model_dump(exclude_unset=True)
                keys = list(knowledge_dict.keys())
                placeholders = [f"${i+1}" for i in range(len(keys))]
                query = f"""
                INSERT INTO {self.settings.KNOWLEDGE_TABLE_NAME} 
                ({', '.join(keys)}) 
                VALUES ({', '.join(placeholders)})
                RETURNING *
                """
                values = [self._prepare_value(knowledge_dict[k]) for k in keys]
                row = await conn.fetchrow(query, *values)
                saved_knowledge.append(self.knowledge_converter.from_db_dict(dict(row)))
            return saved_knowledge

    async def get_knowledge_list(
        self, tenant_id: str, page_params: PageParams[Knowledge]
    ) -> PageResponse[Knowledge]:
        res = await self._get_paginated_data(
            tenant_id, self.settings.KNOWLEDGE_TABLE_NAME, Knowledge, page_params
        )

        # 处理 GitHub 仓库的认证信息
        for item in res.items:
            if (
                item.source_type == KnowledgeSourceEnum.GITHUB_REPO
                and item.source_config
                and hasattr(item.source_config, "auth_info")
            ):
                item.source_config.auth_info = "***"

        return res

    async def get_knowledge(
        self, tenant_id: str, knowledge_id: str
    ) -> Optional[Knowledge]:
        async with self.pool.acquire() as conn:
            query = f"""
            SELECT * FROM {self.settings.KNOWLEDGE_TABLE_NAME}
            WHERE knowledge_id = $1 AND tenant_id = $2
            """
            row = await conn.fetchrow(query, knowledge_id, tenant_id)
            return self.knowledge_converter.from_db_dict(dict(row)) if row else None

    async def update_knowledge(self, knowledge: Knowledge) -> List[Knowledge]:
        async with self.pool.acquire() as conn:
            knowledge_dict = knowledge.model_dump(exclude_unset=True)
            keys = list(knowledge_dict.keys())
            values = [knowledge_dict[k] for k in keys]

            set_clause = ", ".join([f"{k} = ${i+1}" for i, k in enumerate(keys)])
            query = f"""
            UPDATE {self.settings.KNOWLEDGE_TABLE_NAME}
            SET {set_clause}
            WHERE knowledge_id = ${len(keys) + 1}
            RETURNING *
            """

            row = await conn.fetchrow(query, *values, knowledge.knowledge_id)
            return [Knowledge(**dict(row))] if row else []

    async def delete_knowledge(
        self, tenant_id: str, knowledge_id_list: List[str]
    ) -> List[Knowledge]:
        if not knowledge_id_list:
            return []

        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await self.delete_knowledge_task(tenant_id, knowledge_id_list)

                    await self.delete_knowledge_chunk(tenant_id, knowledge_id_list)

                    query = f"""
                            DELETE FROM {self.settings.KNOWLEDGE_TABLE_NAME}
                            WHERE knowledge_id = ANY($1)
                            AND tenant_id = $2
                            RETURNING *
                        """
                    rows = await conn.fetch(query, knowledge_id_list, tenant_id)

                    return [Knowledge(**dict(row)) for row in rows]

        except asyncpg.ForeignKeyViolationError as e:
            self.logger.error(f"Foreign key violation in delete_knowledge: {e}")
            raise HTTPException(
                status_code=400,
                detail="Cannot delete knowledge due to existing dependencies",
            )
        except Exception as e:
            self.logger.error(f"Error in delete_knowledge: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete knowledge")

    # =============== Chunk ===============
    async def save_chunk_list(self, chunk_list: List[Chunk]) -> List[Chunk]:
        if not chunk_list:
            return []

        async with self.pool.acquire() as conn:
            saved_chunks = []
            for chunk in chunk_list:
                chunk_dict = chunk.model_dump(exclude_unset=True, exclude_none=True)
                keys = list(chunk_dict.keys())
                placeholders = [f"${i+1}" for i in range(len(keys))]
                query = f"""
                INSERT INTO {self.settings.CHUNK_TABLE_NAME} 
                ({', '.join(keys)}) 
                VALUES ({', '.join(placeholders)})
                RETURNING *
                """
                values = [self._prepare_value(chunk_dict[k]) for k in keys]
                row = await conn.fetchrow(query, *values)
                saved_chunks.append(self.chunk_converter.from_db_dict(dict(row)))

            return saved_chunks

    async def get_chunk_list(
        self, tenant_id: str, page_params: PageParams[Chunk]
    ) -> PageResponse[Chunk]:
        return await self._get_paginated_data(
            tenant_id,
            self.settings.CHUNK_TABLE_NAME,
            Chunk,
            page_params,
        )

    async def get_chunk_by_id(self, tenant_id: str, chunk_id: str) -> Optional[Chunk]:
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                        SELECT * FROM {self.settings.CHUNK_TABLE_NAME}
                        WHERE chunk_id = $1 AND tenant_id = $2
                    """
                row = await conn.fetchrow(query, chunk_id, tenant_id)

                return self.chunk_converter.from_db_dict(dict(row)) if row else None

        except Exception as e:
            self.logger.error(f"Error in get_chunk_by_id: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve chunk")

    async def delete_knowledge_chunk(
        self, tenant_id: str, knowledge_ids: List[str]
    ) -> List[Chunk]:
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    DELETE FROM {self.settings.CHUNK_TABLE_NAME}
                    WHERE knowledge_id = ANY($1)
                    AND tenant_id = $2
                    RETURNING *
                """
                rows = await conn.fetch(query, knowledge_ids, tenant_id)

                return [self.chunk_converter.from_db_dict(dict(row)) for row in rows]

        except Exception as e:
            self.logger.error(f"Error in delete_knowledge_chunk: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete chunks")

    async def delete_chunk_by_id(
        self, tenant_id: str, chunk_id: str, model_name: str
    ) -> Chunk:
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    DELETE FROM {self.settings.CHUNK_TABLE_NAME}
                    WHERE tenant_id = ANY($1)
                    AND chunk_id = $2
                    AND embedding_model_name = $3
                    RETURNING *
                """
                rows = await conn.fetch(query, tenant_id, chunk_id, model_name)

                return [self.chunk_converter.from_db_dict(dict(row)) for row in rows]

        except Exception as e:
            self.logger.error(f"Error in delete_chunk: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete chunks")

    # =============== Task ===============
    async def save_task_list(self, task_list: List[Task]) -> List[Task]:
        async with self.pool.acquire() as conn:
            saved_tasks = []
            for task in task_list:
                task_dict = task.model_dump(exclude_unset=True, exclude_none=True)
                keys = list(task_dict.keys())
                placeholders = [f"${i+1}" for i in range(len(keys))]

                query = f"""
                INSERT INTO {self.settings.TASK_TABLE_NAME} 
                ({', '.join(keys)}) 
                VALUES ({', '.join(placeholders)})
                RETURNING *
                """
                values = [task_dict[k] for k in keys]
                row = await conn.fetchrow(query, *values)
                saved_tasks.append(self.task_converter.from_db_dict(dict(row)))

            return saved_tasks

    async def update_task_list(self, task_list: List[Task]) -> List[Task]:
        async with self.pool.acquire() as conn:
            updated_tasks = []
            for task in task_list:
                task_dict = task.model_dump(exclude_unset=True, exclude_none=True)
                keys = list(task_dict.keys())
                values = [task_dict[k] for k in keys]

                set_clause = ", ".join([f"{k} = ${i+1}" for i, k in enumerate(keys)])
                query = f"""
                UPDATE {self.settings.TASK_TABLE_NAME}
                SET {set_clause}
                WHERE task_id = ${len(keys) + 1}
                RETURNING *
                """

                row = await conn.fetchrow(query, *values, task.task_id)
                if row:
                    updated_tasks.append(self.task_converter.from_db_dict(dict(row)))

            return updated_tasks

    async def get_task_list(
        self, tenant_id: str, page_params: PageParams[Task]
    ) -> PageResponse[Task]:
        return await self._get_paginated_data(
            tenant_id,
            self.settings.TASK_TABLE_NAME,
            Task,
            page_params,
        )

    async def get_task_by_id(self, tenant_id: str, task_id: str) -> Task | None:
        """
        Retrieve a specific task by its task ID
        """
        try:
            async with self.pool.acquire() as conn:
                query = f"""
                    SELECT * FROM {self.settings.TASK_TABLE_NAME}
                    WHERE tenant_id = $1 AND task_id = $2
                """
                row = await conn.fetchrow(query, tenant_id, task_id)

                if row:
                    return self.task_converter.from_db_dict(dict(row))
                return None

        except Exception as e:
            self.logger.error(f"Error in get_task_by_id: {str(e)}")
            raise

    async def delete_knowledge_task(
        self, tenant_id: str, knowledge_ids: List[str]
    ) -> List[Task] | None:
        """
        Delete tasks associated with the specified knowledge IDs
        """
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    query = f"""
                        DELETE FROM {self.settings.TASK_TABLE_NAME}
                        WHERE knowledge_id = ANY($1)
                        AND tenant_id = $2
                        RETURNING *
                    """
                    rows = await conn.fetch(query, knowledge_ids, tenant_id)

                    if rows:
                        return [
                            self.task_converter.from_db_dict(dict(row)) for row in rows
                        ]
                    return None

        except Exception as e:
            self.logger.error(f"Error in delete_knowledge_task: {str(e)}")
            raise

    # =============== Tenant ===============
    async def save_tenant(self, tenant: Tenant) -> Optional[Tenant]:
        self.logger.info(f"save tenant: {tenant.tenant_name}")
        async with self.pool.acquire() as conn:
            tenant_dict = tenant.model_dump(exclude_none=True)
            keys = list(tenant_dict.keys())
            placeholders = [f"${i+1}" for i in range(len(keys))]

            query = f"""
            INSERT INTO {self.settings.TENANT_TABLE_NAME} 
            ({', '.join(keys)}) 
            VALUES ({', '.join(placeholders)})
            RETURNING *
            """

            values = [tenant_dict[k] for k in keys]
            row = await conn.fetchrow(query, *values)
            return self.tenant_converter.from_db_dict(dict(row)) if row else None

    async def get_tenant_by_sk(self, secret_key: str) -> Optional[Tenant]:
        async with self.pool.acquire() as conn:
            query = f"""
            SELECT * FROM {self.settings.TENANT_TABLE_NAME}
            WHERE secret_key = $1
            """
            row = await conn.fetchrow(query, secret_key)
            return self.tenant_converter.from_db_dict(dict(row)) if row else None

    async def validate_tenant_name(self, tenant_name: str) -> bool:
        async with self.pool.acquire() as conn:
            query = f"""
            SELECT tenant_name FROM {self.settings.TENANT_TABLE_NAME}
            WHERE tenant_name = $1
            """
            exists = await conn.fetchval(query, tenant_name)
            return not bool(exists)

    async def update_tenant(self, tenant: Tenant) -> Optional[Tenant]:
        try:
            async with self.pool.acquire() as conn:
                tenant_data = self.tenant_converter.to_db_dict(tenant)

                columns = list(tenant_data.keys())
                values = [tenant_data[col] for col in columns]

                placeholders = [f"${i+1}" for i in range(len(values))]

                update_sets = [
                    f"{col} = EXCLUDED.{col}" for col in columns if col != "tenant_id"
                ]

                query = f"""
                        INSERT INTO {self.settings.TENANT_TABLE_NAME}
                        ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                        ON CONFLICT (tenant_id)
                        DO UPDATE SET {', '.join(update_sets)}
                        RETURNING *
                    """

                row = await conn.fetchrow(query, *values)

                if row:
                    return Tenant(**dict(row))
                return None

        except asyncpg.UniqueViolationError as e:
            self.logger.error(f"Unique constraint violation in update_tenant: {e}")
            raise HTTPException(
                status_code=409, detail="Tenant with this identifier already exists"
            )
        except Exception as e:
            self.logger.error(f"Error in update_tenant: {e}")
            raise HTTPException(status_code=500, detail="Failed to update tenant")

    # =============== Retrieval ===============
    async def search_space_chunk_list(
        self,
        tenant_id: str,
        params: RetrievalBySpaceRequest,
    ) -> List[RetrievalChunk]:
        """
        search similar chunks based on space_id
        """
        try:
            embedding_model = get_register(
                RegisterTypeEnum.EMBEDDING, params.embedding_model_name
            )
            query_embedding = await embedding_model().embed_text(params.question, 10)

            query = """
            WITH filtered_chunks AS (
                SELECT c.*,
                    c.embedding <=> $1 as similarity
                FROM chunks c
                INNER JOIN knowledge k ON c.knowledge_id = k.knowledge_id
                WHERE 
                    k.space_id = ANY($2)
                    AND k.tenant_id = $3
                    AND c.embedding_model_name = $4
                    AND ($5::jsonb IS NULL OR c.metadata @> $5::jsonb)
            )
            SELECT 
                chunk_id,
                knowledge_id,
                content,
                metadata,
                embedding_model_name,
                similarity
            FROM filtered_chunks
            WHERE similarity <= $6
            ORDER BY similarity ASC
            LIMIT $7;
            """

            params_dict = {
                "query_embedding": query_embedding,
                "space_id_list": params.space_id_list,
                "tenant_id": tenant_id,
                "embedding_model_name": params.embedding_model_name,
                "metadata_filter": (
                    json.dumps(params.metadata_filter)
                    if params.metadata_filter
                    else None
                ),
                "similarity_threshold": params.similarity_threshold,
                "top": params.top,
            }

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    query,
                    params_dict["query_embedding"],
                    params_dict["space_id_list"],
                    params_dict["tenant_id"],
                    params_dict["embedding_model_name"],
                    params_dict["metadata_filter"],
                    params_dict["similarity_threshold"],
                    params_dict["top"],
                )
                return [
                    self.retrievalChunk_converter.from_db_dict(dict(row))
                    for row in rows
                ]

        except Exception as e:
            self.logger.error(f"Error in search_space_chunk_list: {str(e)}")
            raise

    async def search_knowledge_chunk_list(
        self,
        tenant_id: str,
        params: RetrievalByKnowledgeRequest,
    ) -> List[RetrievalChunk]:
        """
        Search for similar text chunks based on knowledge IDs
        """
        try:
            EmbeddingCls = get_register(
                RegisterTypeEnum.EMBEDDING, params.embedding_model_name
            )
            embedding_instance = EmbeddingCls()
            query_embedding = await embedding_instance.embed_text(params.question, 10)

            query = """
            WITH filtered_chunks AS (
                SELECT c.*,
                    c.embedding <=> $1 as similarity
                FROM chunks c
                WHERE 
                    c.knowledge_id = ANY($2)
                    AND c.tenant_id = $3
                    AND c.embedding_model_name = $4
                    AND ($5::jsonb IS NULL OR c.metadata @> $5::jsonb)
            )
            SELECT 
                chunk_id,
                knowledge_id,
                content,
                metadata,
                embedding_model_name,
                similarity
            FROM filtered_chunks
            WHERE similarity <= $6
            ORDER BY similarity ASC
            LIMIT $7;
            """

            params_dict = {
                "query_embedding": query_embedding,
                "knowledge_id_list": params.knowledge_id_list,
                "tenant_id": tenant_id,
                "embedding_model_name": params.embedding_model_name,
                "metadata_filter": (
                    json.dumps(params.metadata_filter)
                    if params.metadata_filter
                    else None
                ),
                "similarity_threshold": params.similarity_threshold,
                "top": params.top,
            }

            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    query,
                    params_dict["query_embedding"],
                    params_dict["knowledge_id_list"],
                    params_dict["tenant_id"],
                    params_dict["embedding_model_name"],
                    params_dict["metadata_filter"],
                    params_dict["similarity_threshold"],
                    params_dict["top"],
                )

                return [
                    self.retrievalChunk_converter.from_db_dict(dict(row))
                    for row in rows
                ]

        except Exception as e:
            self.logger.error(f"Error in search_knowledge_chunk_list: {str(e)}")
            raise

    async def retrieve(
        self,
        tenant_id: str,
        params: RetrievalRequest,
    ) -> List[RetrievalChunk]:
        pass
