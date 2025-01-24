import json
import os
from whiskerrag_utils.embedding import handle


MAX_RETRY_COUNT = 5


# 根据资源类型，处理不同的业务。
def lambda_handler(event, context):
    print(f"++event: {event}")
    output_queue_url = os.getenv("OUTPUT_QUEUE_URL")
    print(f"OUTPUT_QUEUE_URL: {output_queue_url}")
    bucket_name = os.getenv("AWS_BUCKET_NAME")
    print(f"AWS_BUCKET_NAME: {bucket_name}")
    if event:
        sqs_batch_response = {}
        for record in event["Records"]:
            body = record["body"]
            print(f"r++eceive message here: {body}")
            message_dict = json.loads(body)
        return sqs_batch_response
