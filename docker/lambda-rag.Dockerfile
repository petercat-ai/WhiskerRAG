# docker/lambda-rag.Dockerfile
FROM public.ecr.aws/lambda/python:3.9

COPY lambda/rag_task ${LAMBDA_TASK_ROOT}
COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN pip install -r ${LAMBDA_TASK_ROOT}/requirements.txt

CMD ["app.handler"]
