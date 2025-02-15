from typing import List
from dao.base import BaseDAO, get_env_variable

from whiskerrag_types.model import Chunk


class ChunkDao(BaseDAO):

    def __init__(self):
        self.CHUNK_TABLE_NAME = get_env_variable("CHUNK_TABLE_NAME", "chunk")

    def save_chunk_list(self, chunk_list: List[Chunk]):
        self.client.table(self.CHUNK_TABLE_NAME).insert(
            [
                chunk.model_dump(exclude_unset=True, exclude_none=True)
                for chunk in chunk_list
            ]
        ).execute()
