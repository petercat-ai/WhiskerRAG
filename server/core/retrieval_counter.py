import threading
import time
from collections import defaultdict
from whiskerrag_types.model import RetrievalChunk

from core.plugin_manager import PluginManager
from core.log import logger


class RetrivalCounter:
    def __init__(self, flush_interval=60, shards=16):
        self.flush_interval = flush_interval
        self.shards = shards
        self.active_buffers = [defaultdict(int) for _ in range(shards)]
        self.backup_buffers = [defaultdict(int) for _ in range(shards)]
        self.locks = [threading.Lock() for _ in range(shards)]
        self.running = True
        self.flush_thread = threading.Thread(target=self._flush_loop)
        self.flush_thread.start()

    def _get_shard(self, key):
        """根据 Key 的哈希值选择分片"""
        return hash(key) % self.shards

    def record(self, key, count=1):
        shard_id = self._get_shard(key)
        with self.locks[shard_id]:
            self.active_buffers[shard_id][key] += count

    def batch_record(self, records: dict[str, int]):
        if not records:
            return
        for key, count in records.items():
            self.record(key, count)

    def _flush_loop(self):
        while self.running:
            time.sleep(self.flush_interval)
            self._flush()

    def _flush(self):
        """切换缓冲区并写入数据库"""
        # 1. 切换所有分片的缓冲区
        for i in range(self.shards):
            with self.locks[i]:
                self.active_buffers[i], self.backup_buffers[i] = (
                    self.backup_buffers[i],
                    self.active_buffers[i],
                )

        # 2. 合并所有分片的数据并写入数据库
        merged_data = defaultdict(int)
        for buf in self.backup_buffers:
            for key, count in buf.items():
                merged_data[key] += count
        is_success = self._write_to_database(merged_data)
        if is_success:
            # 3. 清空备份缓冲区
            for buf in self.backup_buffers:
                buf.clear()

    def _write_to_database(self, data) -> bool:
        db = PluginManager().dbPlugin
        try:
            db.batch_update_knowledge_retrieval_count(data)
        except Exception as e:
            logger.error(f"flushing konwledge retrival count error: {e}")
            return False
        logger.info(f"flushing konwledge retrival count success: {dict(data)}")
        return True


_counter = RetrivalCounter()


def retrival_counter(chunks: list[RetrievalChunk]):
    _counter.batch_record(
        {k: 1 for k in list(set([chunk.knowledge_id for chunk in chunks]))}
    )
