# AWS Lambda Git 集成指南

本文档详细介绍如何在 WhiskerRAG 项目中集成 Git 功能，使 AWS Lambda 函数能够处理 GitHub 仓库。

## 概述

为了在 AWS Lambda 中使用 GitPython 库处理 GitHub 仓库，我们需要：

1. 添加 Git Lambda Layer 来提供 Git 二进制文件
2. 配置环境变量
3. 添加 GitPython 依赖
4. 实现 Git 环境初始化

## 已实现的配置

### 1. Lambda Layer 配置

在 `template_task.yml` 和 `template_server.yml` 中已添加：

```yaml
Layers:
  # Git Lambda Layer 支持
  - !Sub 'arn:aws:lambda:${AWS::Region}:553035198032:layer:git-lambda2:8'
```

**重要说明：**
- 使用的是 `git-lambda2:8`，这是为 Amazon Linux 2 运行时优化的版本
- 如果使用较老的运行时，应使用 `git:14` 代替
- Layer ARN 会根据部署的 AWS 区域自动调整

### 2. 环境变量配置

已添加以下环境变量：

```yaml
Environment:
  Variables:
    GIT_PYTHON_REFRESH: quiet
    GIT_EXEC_PATH: /opt/bin
```

这些变量确保：
- `GIT_PYTHON_REFRESH: quiet` - 禁止 GitPython 的初始化警告
- `GIT_EXEC_PATH: /opt/bin` - 指向 Lambda Layer 中 Git 二进制文件的位置

### 3. 依赖管理

在 `lambda_task_subscriber/requirements.txt` 中添加：

```
GitPython==3.1.43
```

## Git 配置模块

### `lambda_task_subscriber/git_config.py`

这个模块提供了在 Lambda 环境中配置和使用 Git 的工具函数：

#### 主要功能

1. **`configure_git_environment()`**
   - 配置 Git 环境变量
   - 设置 PATH 确保能找到 Git 二进制文件
   - 配置基本的 Git 全局设置

2. **`clone_repository(repo_url, local_path=None, branch=None, depth=1)`**
   - 在 Lambda 环境中安全地克隆 Git 仓库
   - 默认使用 shallow clone (depth=1) 以提高性能
   - 自动在 `/tmp` 目录下创建工作空间

3. **`test_git_functionality()`**
   - 测试 Git 命令是否可用
   - 用于验证环境配置是否成功

#### 使用示例

```python
from git_config import clone_repository, configure_git_environment

# 配置环境
configure_git_environment()

# 克隆仓库
repo = clone_repository("https://github.com/user/repo.git")

# 访问仓库文件
for root, dirs, files in os.walk(repo.working_dir):
    for file in files:
        if file.endswith('.md'):
            file_path = os.path.join(root, file)
            with open(file_path, 'r') as f:
                content = f.read()
                # 处理文件内容
```

## 部署步骤

### 1. 更新 CloudFormation 模板

确保您的 CloudFormation 模板包含了上述配置。如果从较老版本升级，请：

1. 检查 `template_task.yml` 和 `template_server.yml` 中的 Layers 配置
2. 验证环境变量设置
3. 确认运行时版本与 Layer 版本兼容

### 2. 部署更新

```bash
# 部署任务处理函数
sam deploy --template-file template_task.yml --stack-name whisker-rag-task

# 部署服务器函数
sam deploy --template-file template_server.yml --stack-name whisker-rag-server
```

### 3. 验证部署

部署完成后，检查 Lambda 函数日志确认 Git 环境初始化成功：

```
初始化 Git 环境...
Git 环境配置成功
Git 命令测试成功
Git 功能测试通过
```

## 支持的 AWS 区域

Git Lambda Layer 在以下区域可用：
- us-east-1, us-east-2, us-west-1, us-west-2
- eu-west-1, eu-west-2, eu-west-3, eu-central-1
- ap-northeast-1, ap-northeast-2, ap-southeast-1, ap-southeast-2
- 其他主要 AWS 区域

## 故障排除

### 常见问题

1. **"git command not found" 错误**
   - 检查 Lambda Layer 是否正确添加
   - 验证 `GIT_EXEC_PATH` 环境变量
   - 确认使用了正确的 Layer 版本

2. **"Failed to initialize: Bad git executable" 错误**
   - 检查 `GIT_PYTHON_REFRESH` 环境变量
   - 确认 Git Layer ARN 区域匹配

3. **权限错误**
   - 确保在 `/tmp` 目录下进行 Git 操作
   - 检查 Lambda 函数的执行角色权限

### 调试技巧

1. **启用详细日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **测试 Git 环境**
   ```python
   from git_config import test_git_functionality
   test_git_functionality()
   ```

3. **检查环境变量**
   ```python
   import os
   print("PATH:", os.environ.get('PATH'))
   print("GIT_EXEC_PATH:", os.environ.get('GIT_EXEC_PATH'))
   ```

## 性能考虑

1. **使用 Shallow Clone**
   - 默认使用 `depth=1` 减少下载时间
   - 对于大型仓库尤其重要

2. **缓存策略**
   - 考虑使用 S3 缓存已克隆的仓库
   - 实现增量更新机制

3. **超时设置**
   - 确保 Lambda 函数超时设置足够长
   - 当前设置为 300 秒（5分钟）

## 安全考虑

1. **私有仓库访问**
   - 使用 AWS Secrets Manager 存储 GitHub token
   - 配置适当的 IAM 权限

2. **网络安全**
   - 考虑在 VPC 中运行 Lambda 函数
   - 使用 NAT Gateway 进行出站连接

## 相关资源

- [Git Lambda Layer GitHub 仓库](https://github.com/lambci/git-lambda-layer)
- [GitPython 官方文档](https://gitpython.readthedocs.io/)
- [AWS Lambda Layers 文档](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html) 