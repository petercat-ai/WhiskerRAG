import json
import os
from whiskerrag_types.model import Task, Knowledge, TaskStatus
from whiskerrag_utils.registry import init_register, get_register
import boto3
import asyncio


async def _handle_task(task: Task, knowledge: Knowledge):
    try:
        init_register()
        loader = get_register(knowledge.source_type)
        model = get_register(knowledge.embedding_model_name)
        documents = await loader(knowledge).load()
        chunk_list = await model().embed(knowledge, documents)
        task.status = TaskStatus.SUCCESS
        return {"task": task, "knowledge": knowledge, "chunk": chunk_list}
    except Exception as e:
        print(f"Error parsing task or knowledge: {e}")
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        return {"task": task, "knowledge": knowledge, "chunk": []}


async def _batch_execute_task(records):
    output_queue_url = os.getenv("OUTPUT_QUEUE_URL")
    print(f"OUTPUT_QUEUE_URL: {output_queue_url}")
    output_messages = []
    for record in records:
        try:
            body = record["body"]
            if isinstance(body, str):
                body = json.loads(body)
            if "task" not in body or "knowledge" not in body:
                raise ValueError("Missing 'task' or 'knowledge' in the record body")
            task = Task(**body["task"])
            knowledge = Knowledge(**body["knowledge"])
            res = await _handle_task(task, knowledge)
            output_messages.append(res)
        except Exception as e:
            print(f"Error parsing record: {e}, record: {record}")

    print(f"Output messages: {output_messages}")
    sqs = boto3.client("sqs")
    response = sqs.send_message(
        QueueUrl=output_queue_url, MessageBody=json.dumps(output_messages)
    )
    print(f"Message sent to SQS : {response}")


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
