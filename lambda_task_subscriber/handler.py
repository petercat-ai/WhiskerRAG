import json
import os
from typing import List, TypedDict
from whiskerrag_types.model import Task, Knowledge, TaskStatus
from whiskerrag_utils.registry import init_register, get_register
import boto3
import asyncio
import json
import boto3


class MessageType(TypedDict):
    task: dict
    knowledge: dict
    chunks: List[dict]


def store_message(s3_key: str, message_data: MessageType):
    s3_client = boto3.client("s3")
    bucket_name = os.getenv("S3_TEMP_BUCKET_NAME")
    try:
        s3_client.put_object(
            Bucket=bucket_name, Key=s3_key, Body=json.dumps(message_data)
        )
        reference_message = {
            "message_type": "reference",
            "bucket": bucket_name,
            "key": s3_key,
        }
        return reference_message
    except Exception as e:
        print(f"Error: {e}")
        raise


def send_messages(output_messages, max_retries=3):
    try:
        output_queue_url = os.getenv("OUTPUT_QUEUE_URL")
        print(f"OUTPUT_QUEUE_URL: {output_queue_url}")
        print(f"Output messages: {output_messages}")
        sqs = boto3.client("sqs")
        # Notice: MessageBody max size: 256kb
        response = sqs.send_message(
            QueueUrl=output_queue_url, MessageBody=json.dumps(output_messages)
        )
        print(f"Message sent to SQS : {response}")
    except Exception as e:
        print(f"Error sending messages to SQS: {e}")
        if max_retries > 0:
            print(f"Retrying... {max_retries} attempts left")
            half = len(output_messages) // 2
            send_messages(output_messages[:half], max_retries - 1)
            send_messages(output_messages[half:], max_retries - 1)
        else:
            print("Max retries reached. Failed to send messages.")
            raise


async def _handle_task(task: Task, knowledge: Knowledge):
    execute_result: MessageType = {}
    try:
        init_register()
        loader = get_register(knowledge.source_type)
        model = get_register(knowledge.embedding_model_name)
        documents = await loader(knowledge).load()
        chunk_list = await model().embed(knowledge, documents)
        print(f"Task: {task.model_dump()}")
        task.status = TaskStatus.SUCCESS
        execute_result = {
            "task": task.model_dump(),
            "knowledge": knowledge.model_dump(),
            "chunks": [chunk.model_dump() for chunk in chunk_list],
        }
    except Exception as e:
        print(f"Error parsing task or knowledge: {e}")
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        execute_result = {
            "task": task.model_dump(),
            "knowledge": knowledge.model_dump(),
            "chunks": [],
        }
    s3_key = f"messages/{knowledge.knowledge_id}/{task.task_id}.json"
    reference = store_message(s3_key, execute_result)
    return reference


async def _batch_execute_task(records):
    output_messages = []
    for record in records:
        try:
            body = record["body"]
            if not body:
                raise ValueError("Record body is missing")
            if isinstance(body, str):
                body = json.loads(body)
            tasks = body if isinstance(body, list) else [body]
            for item in tasks:
                if "task" not in item or "knowledge" not in item:
                    raise ValueError(
                        "Missing 'task' or 'knowledge' in the record body item"
                    )
                task = Task(**item["task"])
                knowledge = Knowledge(**item["knowledge"])
                res = await _handle_task(task, knowledge)
                output_messages.append(res)
        except Exception as e:
            print(f"Error parsing record: {e}, record: {record}")
    send_messages(output_messages)


def lambda_handler(event, context):
    try:
        if event:
            print(f"Event: {event},type:{type(event)}; Context: {context},")
            asyncio.run(_batch_execute_task(event.get("Records", [])))
        else:
            raise Exception("No event data found")
        return {"statusCode": 200, "message": "Success"}
    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "message": f"{e}"}
