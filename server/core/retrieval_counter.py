import asyncio
import threading
import traceback
from collections import defaultdict

from .log import logger
from .plugin_manager import PluginManager
from whiskerrag_types.interface import DBPluginInterface
from whiskerrag_types.model import RetrievalChunk


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
        self.stop_event = threading.Event()
        self._shutdown_called = False
        self.flush_thread = threading.Thread(
            target=self._flush_loop, 
            name=f"RetrievalCounter-{id(self)}",
            daemon=True
        )
        self.flush_thread.start()

    def _get_shard(self, key):
        return hash(key) % self.shards

    def record(self, key, count=1):
        if not self.running:
            return
        shard_id = self._get_shard(key)
        with self.locks[shard_id]:
            if len(self.active_buffers[shard_id]) >= self.max_buffer_size:
                self._flush()
            self.active_buffers[shard_id][key] += count

    def batch_record(self, records: dict[str, int]):
        if not records or not self.running:
            return
        for key, count in records.items():
            self.record(key, count)

    def _flush_loop(self):
        try:
            while self.running:
                if self.stop_event.wait(timeout=self.flush_interval):
                    break
                if self.running:
                    self._flush()
        except Exception as e:
            logger.error(f"Error in flush loop: {e}")
        finally:
            logger.debug(f"Flush thread {threading.current_thread().name} exited")

    def _flush(self):
        """Switch buffers and write to the database"""
        if not self.running:
            return
            
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
            return True
        
        if not self.running:
            return False
        
        # Check if db_plugin is available
        if self.db_plugin is None:
            try:
                self.db_plugin = PluginManager().dbPlugin
            except Exception as e:
                logger.warning(f"Database plugin not available: {e}")
                return False
        
        if self.db_plugin is None:
            logger.warning("Database plugin is None, skipping flush")
            return False
        
        try:
            asyncio.run(self.db_plugin.batch_update_knowledge_retrieval_count(data))
            logger.debug(f"Flushed {len(data)} retrieval counts successfully")
            return True
        except Exception:
            logger.error(f"Error flushing retrieval counts: {traceback.format_exc()}")
            return False

    def force_flush(self):
        """Force flush all buffers immediately"""
        if self.running:
            self._flush()

    def shutdown(self):
        if self._shutdown_called:
            return
        
        logger.debug("Shutting down RetrievalCounter")
        self._shutdown_called = True
        self.running = False
        self.stop_event.set()
        
        # Final flush
        try:
            self.force_flush()
        except Exception as e:
            logger.warning(f"Error during final flush: {e}")
        
        # Wait for thread to finish
        if self.flush_thread.is_alive():
            self.flush_thread.join(timeout=3.0)
            if self.flush_thread.is_alive():
                logger.warning(f"Flush thread did not finish within timeout")


def retrieval_count(counter: RetrievalCounter, chunks: list[RetrievalChunk]):
    counter.batch_record(
        {k: 1 for k in list(set([chunk.knowledge_id for chunk in chunks]))}
    )


_retrieval_counter: RetrievalCounter | None = None


def get_retrieval_counter() -> RetrievalCounter:
    global _retrieval_counter
    if _retrieval_counter is None:
        # Initialize with None db_plugin, it will be set when available
        try:
            db_plugin = PluginManager().dbPlugin
        except Exception:
            # Plugin not available yet, will be set later
            db_plugin = None
            
        _retrieval_counter = RetrievalCounter(
            flush_interval=60, shards=16, db_plugin=db_plugin
        )
    return _retrieval_counter


def shutdown_retrieval_counter():
    """Shutdown the global retrieval counter"""
    global _retrieval_counter
    if _retrieval_counter is not None:
        _retrieval_counter.shutdown()
        _retrieval_counter = None
        logger.debug("Global retrieval counter shut down")


def initialize_retrieval_counter():
    """Initialize the global retrieval counter"""
    global _retrieval_counter
    # Ensure any existing counter is shut down first
    shutdown_retrieval_counter()
    # The counter will be created on first access via get_retrieval_counter()
    logger.debug("Retrieval counter initialized")
