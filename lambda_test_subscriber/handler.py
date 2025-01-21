import boto3

MAX_RETRY_COUNT = 5


# 根据资源类型，处理不同的业务。
def lambda_handler(event, context):
    if event:
        # sqs = boto3.client("sqs")
        # destination_queue_url = context["destination_queue_url"]
        sqs_batch_response = {}
        for record in event["Records"]:
            body = record["body"]
            print(f"receive message here: {body}")

            # Send message to the destination queue
            # response = sqs.send_message(
            #     QueueUrl=destination_queue_url,
            #     MessageBody=body
            # )
            # print(f"Message sent to destination queue: {response['MessageId']}")

        sqs_batch_response["response"] = "this is response"
        return sqs_batch_response
