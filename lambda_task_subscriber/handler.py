import json


MAX_RETRY_COUNT = 5


# 根据资源类型，处理不同的业务。
def lambda_handler(event, context):
    if event:
        sqs_batch_response = {}
        print(f"event: {event}")
        for record in event["Records"]:
            body = record["body"]
            print(f"receive message here: {body}")
            message_dict = json.loads(body)
        return sqs_batch_response
