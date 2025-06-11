import asyncio
import json
import logging
from typing import Any, Dict, List

from dao.chunk_dao import ChunkDao
from dao.knowledge_dao import KnowledgeDao
from dao.task_dao import TaskDao
from whiskerrag_types.model import (
    Knowledge,
    Task,
    TaskStatus,
)
from whiskerrag_utils import (
    decompose_knowledge,
    get_chunks_by_knowledge,
    get_diff_knowledge_by_sha,
    init_register,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class TaskExecutor:
    def __init__(self):
        self._is_running = False
        self.task_dao = TaskDao()
        self.chunk_dao = ChunkDao()
        self.knowledge_dao = KnowledgeDao()
        self.semaphore = asyncio.Semaphore(50)

    async def handle_add_knowledge_task(self, task: Task, knowledge: Knowledge):
        async with self.semaphore:
            logger.info(f"semaphore is : {self.semaphore}")
            chunk_list = []
            try:
                print("=== start task ===", task.task_id)
                task.update(status=TaskStatus.RUNNING)
                self.task_dao.update_task_list([task])

                # 1. Decompose knowledge
                decomposed_knowledge_list = await decompose_knowledge(knowledge)

                # 2. Get existing knowledge from the database
                db_knowledge_list: List[Knowledge] = (
                    await self.knowledge_dao.get_all_knowledge_list(
                        tenant_id=knowledge.tenant_id,
                        eq_conditions={
                            "space_id": knowledge.space_id,
                            "parent_id": knowledge.knowledge_id,
                        },
                    )
                )

                # 3. Compare knowledge
                diff = get_diff_knowledge_by_sha(
                    db_knowledge_list, decomposed_knowledge_list
                )

                # 4. Handle deletions
                if diff["to_delete"]:
                    delete_ids = [k.knowledge_id for k in diff["to_delete"]]
                    await self.knowledge_dao.delete_knowledge(
                        knowledge.tenant_id, delete_ids
                    )

                # 5. Handle additions and get chunks for new knowledge
                if diff["to_add"]:
                    added_knowledge_list = await self.knowledge_dao.add_knowledge_list(
                        knowledge.tenant_id, diff["to_add"]
                    )
                    for new_knowledge_item in added_knowledge_list:
                        chunks = await get_chunks_by_knowledge(new_knowledge_item)
                        chunk_list.extend(chunks)

                logger.info(f"Successfully processed task: {task.task_id}")
                task.update(status=TaskStatus.SUCCESS)
            except asyncio.CancelledError:
                logger.warning(f"Task {task.task_id} was cancelled")
                task.update(
                    status=TaskStatus.FAILED, error_message="Task was cancelled"
                )
                raise
            except asyncio.TimeoutError:
                logger.error(f"Task {task.task_id} timed out after 60 seconds")
                task.status = TaskStatus.FAILED
                task.error_message = f"Task timed out after 60 seconds, you can try again or reset knowledge split config"
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error processing task {task.task_id}: {str(e)}")
                task.update(status=TaskStatus.FAILED, error_message=str(e))
            finally:
                logger.info(f"=== End task ===: {task.task_id}")
                if chunk_list and len(chunk_list) > 0:
                    # Save new chunks
                    self.chunk_dao.save_chunk_list(chunk_list)
                self.task_dao.update_task_list([task])

    async def cleanup(self):
        """Clean up any resources"""
        # Cancel any pending tasks if needed
        # This method can be called before shutting down
        pass


_task_executor = TaskExecutor()


def get_task_executor() -> TaskExecutor:
    global _task_executor
    if _task_executor is None:
        _task_executor = TaskExecutor()
    return _task_executor


async def process_single_record(record: Dict[str, Any]) -> tuple[bool, str]:
    try:
        executor = get_task_executor()
        body = record["body"]
        if not body:
            raise ValueError("Record body is missing")

        if isinstance(body, str):
            body = json.loads(body)

        tasks = body if isinstance(body, list) else [body]
        asyncio_task_list = []

        for item in tasks:
            if "task" not in item or "knowledge" not in item:
                raise ValueError(
                    "Missing 'task' or 'knowledge' in the record body item"
                )

            task = Task(**item["task"])
            knowledge = Knowledge(**item["knowledge"])
            asyncio_task_list.append(
                executor.handle_add_knowledge_task(task, knowledge)
            )

        await asyncio.gather(*asyncio_task_list)
        logger.info(f"Successfully processed record {record['messageId']}")
        return True, record["messageId"]

    except Exception as e:
        logger.error(f"Error processing record {record['messageId']}: {str(e)}")
        return False, record["messageId"]


async def handle_records(
    records: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, str]]]:
    failed_records = []
    tasks = [process_single_record(record) for record in records]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for record, result in zip(records, results):
        if isinstance(result, Exception):
            logger.error(
                f"Error processing record {record['messageId']}: {str(result)}"
            )
            failed_records.append({"itemIdentifier": record["messageId"]})
        else:
            success, message_id = result
            if not success:
                failed_records.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failed_records}


def lambda_handler(
    event: Dict[str, Any], context: Any
) -> Dict[str, List[Dict[str, str]]]:
    init_register("whiskerrag_utils")
    try:
        # Create a new event loop for lambda execution
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            records = event.get("Records", [])
            logger.info(f"Processing {len(records)} records")

            result = loop.run_until_complete(handle_records(records))

            failed_count = len(result["batchItemFailures"])
            if failed_count > 0:
                logger.warning(f"{failed_count} records failed and will be retried")

            return result
        finally:
            # Clean up the event loop
            loop.close()

    except Exception as e:
        logger.error(f"Unexpected error in lambda handler: {str(e)}", exc_info=True)
        return {
            "batchItemFailures": [
                {"itemIdentifier": record["messageId"]}
                for record in event.get("Records", [])
            ]
        }


if __name__ == "__main__":
    import traceback

    async def main():
        init_register("whiskerrag_utils")

        knowledge_id = "6f7b68b3-61ef-422c-a994-a3c3960681ce"
        task_id = "eca55ec7-c06e-4f4a-8a4b-64d302e7f4b0"
        tenant_id = "38fbd88b-e869-489c-9142-e4ea2c226e42"
        space_id = "ch-liuzhide/AgentFlow"

        # Example dummy data for a record
        # Please modify the content of task and knowledge according to your actual situation
        dummy_record = {
            "messageId": "test-message-123",
            "body": json.dumps(
                {
                    "task": {
                        "task_id": task_id,
                        "tenant_id": tenant_id,
                        "status": "pending",
                        "space_id": space_id,
                        "created_at": "2023-01-01T00:00:00Z",
                        "updated_at": "2023-01-01T00:00:00Z",
                        "knowledge_id": knowledge_id,
                    },
                    "knowledge": {
                        "knowledge_name": "ch-liuzhide/AgentFlow",
                        "source_type": "github_repo",
                        "knowledge_type": "folder",
                        "space_id": "ch-liuzhide/AgentFlow",
                        "split_config": {
                            "type": "github_repo",
                            "include_patterns": ["*.md"],
                        },
                        "source_config": {
                            "url": "https://github.com",
                            "repo_name": "ch-liuzhide/AgentFlow",
                        },
                        "embedding_model_name": "openai",
                        "metadata": {"url": "xxxx"},
                        "file_sha": "111",
                        "knowledge_id": knowledge_id,
                        "tenant_id": tenant_id,
                        "enabled": True,
                    },
                }
            ),
        }

        # Simulate the event structure received by lambda_handler
        dummy_event = {"Records": [dummy_record]}

        print("Running lambda_handler locally with dummy data...")

        try:
            records = dummy_event.get("Records", [])
            logger.info(f"Processing {len(records)} records")

            result = await handle_records(records)

            failed_count = len(result["batchItemFailures"])
            if failed_count > 0:
                logger.warning(f"{failed_count} records failed and will be retried")

            print("Local execution result:", result)
            return result
        except Exception as e:
            logger.error(f"Unexpected error in main: {str(e)}", exc_info=True)
            return {
                "batchItemFailures": [
                    {"itemIdentifier": record["messageId"]}
                    for record in dummy_event.get("Records", [])
                ]
            }
        finally:
            # Ensure cleanup of any resources
            executor = get_task_executor()
            await executor.cleanup()

            # Wait for a short time to allow any pending operations to complete
            await asyncio.sleep(0.1)

    # Use asyncio.run() for proper event loop management in Python 3.13
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Error in main execution: {e}")
        traceback.print_exc()
    finally:
        # Force garbage collection to clean up any remaining resources
        import gc

        gc.collect()
        traceback.print_exc()
