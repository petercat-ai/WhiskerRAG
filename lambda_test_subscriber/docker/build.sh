#!/bin/sh
if [[ "$SHELL" == *"zsh"* ]]; then
    echo "Running in zsh"
    source ~/.zshrc
elif [[ "$SHELL" == *"bash"* ]]; then
    echo "Running in bash"
    source ~/.bashrc
fi

if [ -z "$AWS_REGION" ]; then
  AWS_REGION="$(aws configure get region)"
  if [ -z "$AWS_REGION" ]; then
    echo "AWS_REGION is not set and could not be retrieved from AWS configuration."
    exit 1
  fi
fi

# 检查并设置 AWS_ACCOUNT_ID
if [ -z "$AWS_ACCOUNT_ID" ]; then
  AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
  if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "AWS_ACCOUNT_ID is not set and could not be retrieved from AWS STS."
    exit 1
  fi
fi

# 设置变量
REPOSITORY_NAME="whisker_rag_test"  # 替换为你的仓库名
IMAGE_TAG="$(date +%Y%m%d%H%M%S)_local"

# 输出变量信息
echo "AWS_REGION: $AWS_REGION"
echo "AWS_ACCOUNT_ID: $AWS_ACCOUNT_ID"
echo "REPOSITORY_NAME: $REPOSITORY_NAME"
echo "IMAGE_TAG: $IMAGE_TAG"

# 登录到 ECR
echo "Logging in to ECR..."
echo "aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
if [ $? -ne 0 ]; then
  echo "Failed to log in to ECR"
  exit 1
fi

# 确保 ECR 仓库存在
echo "Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $AWS_REGION
if [ $? -ne 0 ]; then
  echo "ECR repository does not exist. Exiting..."
  exit 1
fi

# 构建镜像
echo "Building Docker image..."

# Navigate to the directory containing the Dockerfile
cd "$(dirname "$0")"

# Build the Docker image
docker build -f Dockerfile -t $REPOSITORY_NAME:$IMAGE_TAG ../
if [ $? -ne 0 ]; then
  echo "Failed to build Docker image"
  exit 1
fi

# 标记镜像
echo "Tagging image..."
docker tag $REPOSITORY_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPOSITORY_NAME:$IMAGE_TAG

# 询问是否推送
read -p "Do you want to push the image to ECR? (y/n): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" && "$confirm" != "yes" ]]; then
  echo "Push cancelled."
  exit 0
fi

# 推送镜像
echo "Pushing image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPOSITORY_NAME:$IMAGE_TAG

# 验证
echo "Verifying push..."
aws ecr describe-images --repository-name $REPOSITORY_NAME --region $AWS_REGION

echo "Process completed successfully!"