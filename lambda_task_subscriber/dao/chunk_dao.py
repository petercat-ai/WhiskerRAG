from typing import List
from dao.base import BaseDAO, get_env_variable

from whiskerrag_types.model import Chunk


class ChunkDao(BaseDAO):

    def __init__(self):
        self.CHUNK_TABLE_NAME = get_env_variable("CHUNK_TABLE_NAME", "chunk")

    def save_chunk_list(self, chunk_list: List[Chunk]):
        chunk_size = 30
        for i in range(0, len(chunk_list), chunk_size):
            chunk_batch = chunk_list[i : i + chunk_size]
            self.client.table(self.CHUNK_TABLE_NAME).insert(
                [
                    chunk.model_dump(exclude_unset=True, exclude_none=True)
                    for chunk in chunk_batch
                ]
            ).execute()
