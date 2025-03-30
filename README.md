# WhiskerRAG

[English](README.en-US.md) | 简体中文

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/petercat-ai/whiskerrag.svg)](https://github.com/petercat-ai/whiskerrag/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/petercat-ai/whiskerrag.svg)](https://github.com/petercat-ai/whiskerrag/issues)

一个轻量级且灵活的 RAG (检索增强生成) 框架。

## 特性 ✨

- [**感知能力**] WhiskerRAG 是一个轻量级的 RAG 框架，通过高效的信息检索机制增强文本生成能力。

- [**灵活性**] WhiskerRAG 提供插件架构，支持向量数据库和文件嵌入系统的自定义，使用户能够根据特定需求定制 RAG 系统。

- [**多模态**] WhiskerRAG 正在开发多模态 RAG 系统。您可以通过我们的 petercat 服务体验最新功能。

- **即将推出**：
    - Web 界面集成
    - 增强的知识检索能力
    - 知识图谱功能

## 项目结构 📁

```
.
├── server/                 # FastAPI 服务端 
│   ├── api/                # API 接口  
│   ├── plugins/            # 插件模块
│   └── core/               # 项目核心方法  
├── web/                    # WEB 前端（TODO）
├── docker/                 # Docker 镜像  
└── lambda_task_subscriber/ # 亚马逊异步处理任务云函数
```

## 部署 📦

WhiskerRAG 支持多种部署选项，包括本地部署和 AWS 云部署。

### 本地部署

本地部署需要 Docker 环境。使用以下命令：

```bash
docker login

# 构建所有镜像
docker-compose up --build -d
docker-compose up -e API_KEY=mysecretkey -e DEBUG=true -e DB_HOST=postgres

# 启动所有服务
docker-compose start

# 停止所有服务
docker-compose stop

# 重启所有服务
docker-compose restart

# 启动特定服务
docker-compose start postgres

# 停止特定服务
docker-compose stop postgres

# 删除所有服务
docker-compose down
```

环境变量在 `docker-compose.yml` 中预先配置。默认值适用于大多数情况。对于本地开发，请参考 `.env.example` 并创建包含自定义配置的 `.env` 文件。

### AWS Cloud 和 Supabase

为了通过云服务提供增强的系统稳定性，我们提供 AWS 和 Supabase 集成选项。
请确保已准备好 AWS 和 Supabase 环境。在 `.github/workflows/server-deploy.yml` 中配置环境变量：

```bash
TASK_ENGINE_CLASSNAME="AWSLambdaTaskEnginePlugin"
DB_ENGINE_CLASSNAME="SupaBasePlugin"
# 数据库
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_KEY=your-supabase-service-key
# 表名
KNOWLEDGE_TABLE_NAME=knowledge
CHUNK_TABLE_NAME=chunk
TASK_TABLE_NAME=task
ACTION_TABLE_NAME=action
TENANT_TABLE_NAME=tenant
# LLM
OPENAI_API_KEY=your-openai-api-key
# AWS
SQS_QUEUE_URL=your-sqs-queue-url
```

## 高级用法 🚀

### 自定义数据层

考虑到私有部署中多样化的数据存储需求，WhiskerRAG 实现了插件机制，支持自定义数据存储解决方案。参考 `server/local-plugin` 中的实现来创建您自己的接口。

### 自定义 RAG 核心流程

WhiskerRAG 提供贡献点注册机制，允许自定义核心 RAG 流程，包括资源加载、嵌入、分段和检索策略。查看 `server/local-plugin-registry` 获取实现示例。

## 贡献 🤝

我们欢迎贡献！请随时提交 Pull Request。

## 许可证 📄

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

⭐️ 如果您觉得这个项目有帮助，请考虑给它点个星！