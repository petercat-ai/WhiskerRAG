# AWS Lambda Git 集成指南

本文档详细介绍如何在 WhiskerRAG 项目中集成 Git 功能，使 AWS Lambda 函数能够处理 GitHub 仓库。

## 概述

为了在 AWS Lambda 中使用 GitPython 库处理 GitHub 仓库，我们需要：

1. 在 Docker 镜像中安装 Git 二进制文件
2. 配置环境变量
3. 添加 GitPython 依赖
4. 实现 Git 环境初始化

## 已实现的配置

### 1. Docker 镜像配置

由于项目使用 `PackageType: Image`，我们在 Dockerfile 中安装 Git：

**任务函数 (`docker/Dockerfile.aws.task`)**:
```dockerfile
# Install git and other necessary packages
RUN yum update -y && \
    yum install -y git && \
    yum clean all

# Set git environment variables
ENV GIT_PYTHON_REFRESH=quiet
ENV GIT_EXEC_PATH=/usr/bin
```

**服务器函数 (`docker/Dockerfile.aws.server`)**:
```dockerfile
# Install make and git
RUN apt-get update && apt-get install -y make git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set git environment variables
ENV GIT_PYTHON_REFRESH=quiet
ENV GIT_EXEC_PATH=/usr/bin/git
```

**重要说明：**
- 任务函数使用 Amazon Linux 2 基础镜像，使用 `yum` 包管理器
- 服务器函数使用 Debian 基础镜像，使用 `apt-get` 包管理器
- Git 安装在系统标准路径 `/usr/bin/git`

### 2. 环境变量配置

已添加以下环境变量：

```yaml
Environment:
  Variables:
    GIT_PYTHON_REFRESH: quiet
    GIT_EXEC_PATH: /usr/bin  # 或 /usr/bin/git 取决于具体配置
```

这些变量确保：
- `GIT_PYTHON_REFRESH: quiet` - 禁止 GitPython 的初始化警告
- `GIT_EXEC_PATH: /usr/bin` - 指向系统 Git 二进制文件的位置

### 3. 依赖管理

在 `lambda_task_subscriber/requirements.txt` 中添加：

```
gitpython>=3.1.44
```

## Git 配置模块

### `lambda_task_subscriber/git_config.py`

这个模块提供了在 Lambda Docker 环境中配置和使用 Git 的工具函数：

#### 主要功能

1. **`configure_git_environment()`**
   - 自动检测 Git 二进制文件位置
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

### 1. 构建 Docker 镜像

确保您的 Docker 镜像包含了 Git 安装：

```bash
# 构建任务函数镜像
docker build -f docker/Dockerfile.aws.task -t whisker-rag-task .

# 构建服务器函数镜像  
docker build -f docker/Dockerfile.aws.server -t whisker-rag-server .
```

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
init git environment
git environment configured successfully
git command test passed
Git 功能测试通过
```

## Docker vs Lambda Layer 对比

| 方面 | Docker 方式 | Lambda Layer 方式 |
|------|------------|------------------|
| **包类型** | `PackageType: Image` | `PackageType: Zip` |
| **Git 安装** | 在 Dockerfile 中安装 | 使用预构建的 Layer |
| **灵活性** | 完全控制 Git 版本 | 受限于 Layer 版本 |
| **部署大小** | 较大，包含完整系统 | 较小，只有代码 |
| **冷启动** | 可能稍慢 | 通常更快 |
| **维护** | 需要维护 Docker 镜像 | AWS 维护 Layer |

## 故障排除

### 常见问题

1. **"git command not found" 错误**
   - 检查 Dockerfile 中是否正确安装了 Git
   - 验证 `GIT_EXEC_PATH` 环境变量
   - 确认 Docker 镜像构建成功

2. **"Failed to initialize: Bad git executable" 错误**
   - 检查 `GIT_PYTHON_REFRESH` 环境变量
   - 验证 Git 路径配置

3. **权限错误**
   - 确保在 `/tmp` 目录下进行 Git 操作
   - 检查 Lambda 函数的执行角色权限

### 调试技巧

1. **检查 Git 安装**
   ```python
   import os
   import subprocess
   
   # 检查 Git 是否安装
   result = subprocess.run(['which', 'git'], capture_output=True, text=True)
   print("Git location:", result.stdout.strip())
   
   # 检查 Git 版本
   result = subprocess.run(['git', '--version'], capture_output=True, text=True)
   print("Git version:", result.stdout.strip())
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
   print("GIT_PYTHON_REFRESH:", os.environ.get('GIT_PYTHON_REFRESH'))
   ```

## 性能考虑

1. **Docker 镜像优化**
   - 使用多阶段构建减少镜像大小
   - 清理不必要的包和缓存

2. **使用 Shallow Clone**
   - 默认使用 `depth=1` 减少下载时间
   - 对于大型仓库尤其重要

3. **缓存策略**
   - 考虑使用 S3 缓存已克隆的仓库
   - 实现增量更新机制

4. **超时设置**
   - 确保 Lambda 函数超时设置足够长
   - 当前设置为 300 秒（5分钟）

## 安全考虑

1. **私有仓库访问**
   - 使用 AWS Secrets Manager 存储 GitHub token
   - 配置适当的 IAM 权限

2. **网络安全**
   - 考虑在 VPC 中运行 Lambda 函数
   - 使用 NAT Gateway 进行出站连接

3. **Docker 镜像安全**
   - 定期更新基础镜像
   - 扫描镜像安全漏洞

## 相关资源

- [GitPython 官方文档](https://gitpython.readthedocs.io/)
- [AWS Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [Docker 最佳实践](https://docs.docker.com/develop/dev-best-practices/) 