import asyncio
import threading
import traceback
from collections import defaultdict
from whiskerrag_types.model import RetrievalChunk
from whiskerrag_types.interface import DBPluginInterface
from core.log import logger
from core.plugin_manager import PluginManager


class RetrievalCounter:
    max_buffer_size = 100000

    def __init__(
        self, flush_interval=60, shards=16, db_plugin: DBPluginInterface = None
    ):
        self.flush_interval = flush_interval
        self.shards = shards
        self.db_plugin = db_plugin
        self.active_buffers = [defaultdict(int) for _ in range(shards)]
        self.backup_buffers = [defaultdict(int) for _ in range(shards)]
        self.locks = [threading.Lock() for _ in range(shards)]
        self.running = True
        self.stop_event = threading.Event()  # 添加终止事件
        self.flush_thread = threading.Thread(target=self._flush_loop)
        self.flush_thread.daemon = True
        self.flush_thread.start()

    def _get_shard(self, key):
        return hash(key) % self.shards

    def record(self, key, count=1):
        shard_id = self._get_shard(key)
        with self.locks[shard_id]:
            if len(self.active_buffers[shard_id]) >= self.max_buffer_size:
                self._flush()
            self.active_buffers[shard_id][key] += count

    def batch_record(self, records: dict[str, int]):
        if not records:
            return
        for key, count in records.items():
            self.record(key, count)

    def _flush_loop(self):
        while self.running:
            # 使用 wait 替代 sleep，这样可以响应中断
            if self.stop_event.wait(timeout=self.flush_interval):
                break
            self._flush()

    def _flush(self):
        """Switch buffers and write to the database"""
        # 1. Switch the buffers for all shards
        for i in range(self.shards):
            with self.locks[i]:
                self.active_buffers[i], self.backup_buffers[i] = (
                    self.backup_buffers[i],
                    self.active_buffers[i],
                )

        # 2. Merge data from all shards and write to the database
        merged_data = defaultdict(int)
        for buf in self.backup_buffers:
            for key, count in buf.items():
                merged_data[key] += count
        is_success = self._write_to_database(merged_data)
        if is_success:
            # 3. Clear the backup buffers
            for buf in self.backup_buffers:
                buf.clear()

    def _write_to_database(self, data) -> bool:
        if not data:
            logger.info(f"flushing knowledge retrieval count skip: {dict(data)}")
            return False
        try:
            asyncio.run(self.db_plugin.batch_update_knowledge_retrieval_count(data))
            logger.info(f"flushing knowledge retrieval count success: {dict(data)}")
        except Exception:
            logger.error(
                f"flushing knowledge retrieval count error: {traceback.format_exc()}"
            )
            return False

        return True

    def force_flush(self):
        """Force flush all buffers immediately"""
        self._flush()

    def shutdown(self):
        self.running = False
        self.stop_event.set()  # 触发终止事件
        self.force_flush()
        if self.flush_thread.is_alive():
            self.flush_thread.join()


def retrieval_count(counter: RetrievalCounter, chunks: list[RetrievalChunk]):
    counter.batch_record(
        {k: 1 for k in list(set([chunk.knowledge_id for chunk in chunks]))}
    )


_retrieval_counter: RetrievalCounter | None = None


def get_retrieval_counter() -> RetrievalCounter:
    global _retrieval_counter
    if _retrieval_counter is None:
        _retrieval_counter = RetrievalCounter(
            flush_interval=60, shards=16, db_plugin=PluginManager().dbPlugin
        )
    return _retrieval_counter
