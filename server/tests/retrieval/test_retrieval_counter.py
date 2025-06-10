import asyncio
import os
import threading
import time
import unittest

from whiskerrag_types.model import RetrievalChunk
from whiskerrag_utils import init_register

from server.core.plugin_manager import PluginManager
from server.core.retrieval_counter import RetrievalCounter, retrieval_count


class TestRetrievalCounter(unittest.TestCase):
    def setUp(self):
        init_register("whiskerrag_utils")
        plugin_abs_path = (
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/plugins"
        )
        os.environ["DB_ENGINE_CLASSNAME"] = "MockPlugin"
        print(f"plugin_abs_path: {plugin_abs_path}")
        PluginManager(plugin_abs_path)
        db_plugin = PluginManager().dbPlugin
        asyncio.run(db_plugin.ensure_initialized())
        self.counter = RetrievalCounter(flush_interval=1, shards=4, db_plugin=db_plugin)
        self.thread_count = 100
        self.record_per_thread = 100
        self.test_keys = ["t1", "t2", "t3", "t4", "t5"]

    def _concurrent_worker(self, key):
        """并发工作线程"""
        for _ in range(self.record_per_thread):
            self.counter.record(key)
            time.sleep(0.001)  # 增加竞争概率

    def tearDown(self):
        self.counter.db_plugin.reset_retrieval_count()
        self.counter.running = False
        self.counter.flush_thread.join()

    def test_get_shard(self):
        shard_id = self.counter._get_shard("test_key")
        expected_shard_id = shard_id % self.counter.shards
        self.assertEqual(expected_shard_id, shard_id)

    def test_batch_record_empty(self):
        records = {}
        self.counter.batch_record(records)
        self.assertTrue(True)

    def test_batch_record(self):
        records = {"key1": 1, "key2": 2}
        self.counter.batch_record(records)
        for key, count in records.items():
            shard_id = self.counter._get_shard(key)
            with self.counter.locks[shard_id]:
                self.assertEqual(self.counter.active_buffers[shard_id][key], count)
        time.sleep(1.5)
        for key, count in records.items():
            shard_id = self.counter._get_shard(key)
            with self.counter.locks[shard_id]:
                self.assertEqual(self.counter.active_buffers[shard_id][key], 0)

        db_result = self.counter.db_plugin.retrieval_count
        self.assertDictEqual(db_result, records)

    def test_retrieval_counter(self):
        test_chunks = [
            {  # 第一个知识块
                "space_id": "space_1",
                "tenant_id": "tenant_A",
                "context": "text1",
                "knowledge_id": "one",
                "similarity": 0.8,
                "embedding_model_name": "text-embedding-3-small",
            },
            {  # 第二个知识块（同knowledge_id）
                "space_id": "space_1",
                "tenant_id": "tenant_A",
                "context": "text2",
                "knowledge_id": "one",  # 相同knowledge_id
                "similarity": 0.75,
                "embedding_model_name": "text-embedding-3-small",
            },
            {  # 第三个知识块（不同knowledge_id）
                "space_id": "space_2",
                "tenant_id": "tenant_B",
                "context": "text3",
                "knowledge_id": "two",
                "similarity": 0.85,
                "embedding_model_name": "text-embedding-ada-002",
            },
        ]

        # 转换为模型实例列表
        chunks = [RetrievalChunk(**data) for data in test_chunks]
        retrieval_count(self.counter, chunks)
        self.counter.force_flush()
        db_result = self.counter.db_plugin.retrieval_count
        expected = {"one": 1, "two": 1}
        self.assertEqual(
            db_result, expected, f"Expected {expected} but got {db_result}"
        )

    def test_high_concurrency_single_key(self):
        """测试单个key的极高并发"""
        test_key = "concurrent_key"
        threads = []
        for _ in range(self.thread_count):
            t = threading.Thread(target=self._concurrent_worker, args=(test_key,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 强制立即刷新
        self.counter.force_flush()

        # 验证计数
        expected = self.thread_count * self.record_per_thread
        db_result = self.counter.db_plugin.retrieval_count.get(test_key, 0)
        self.assertEqual(
            db_result, expected, f"Expected {expected} but got {db_result}"
        )

    def test_high_concurrency_multiple_keys(self):
        """测试多个key的并发写入"""

        threads = []
        for key in self.test_keys:
            for _ in range(self.thread_count):
                t = threading.Thread(target=self._concurrent_worker, args=(key,))
                threads.append(t)
                t.start()

        for t in threads:
            t.join()

        self.counter.force_flush()

        # 验证每个key的计数
        expected_per_key = self.thread_count * self.record_per_thread
        for key in self.test_keys:
            actual = self.counter.db_plugin.retrieval_count.get(key, 0)
            self.assertEqual(
                actual,
                expected_per_key,
                f"Key {key} expected {expected_per_key} got {actual}",
            )

    def test_mixed_concurrency(self):
        """混合并发测试: 同时有record和batch_record操作"""
        shared_key = "shared_key"

        def batch_worker():
            for _ in range(100):
                self.counter.batch_record({k: 1 for k in self.test_keys})
                self.counter.batch_record({shared_key: 2})

        # 启动两种类型的worker
        threads = []
        for _ in range(5):
            t = threading.Thread(target=self._concurrent_worker, args=(shared_key,))
            threads.append(t)
            t = threading.Thread(target=batch_worker)
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.counter.force_flush()

        # 验证独立key
        expected_independent = 5 * 100 * 1  # 5个batch_worker各100次
        for key in self.test_keys:
            actual = self.counter.db_plugin.retrieval_count.get(key, 0)
            self.assertEqual(
                actual,
                expected_independent,
                f"Key {key} expected {expected_independent} got {actual}",
            )

        # 验证共享key
        expected_shared = (5 * self.record_per_thread) + (
            5 * 100 * 2
        )  # concurrent_worker + batch_worker
        actual_shared = self.counter.db_plugin.retrieval_count.get(shared_key, 0)
        self.assertEqual(
            actual_shared,
            expected_shared,
            f"Shared key expected {expected_shared} got {actual_shared}",
        )


if __name__ == "__main__":
    unittest.main()
