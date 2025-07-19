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


## 高级用法 🚀
RAG 项目在真实落地中就会发现，定制化需求极高。这和大家的数据存储方案、运行资源有极大的关系，大部分企业级项目都有自己的规范，因此与其他开源项目 ragflow，llamindex 不同，WhiskerRAG 的核心是提供插件机制，支持每个项目通过编写插件的形式自定义数据入库、数据存储、向量存储、召回方案。参考 `server/local_plugin` 中的实现来创建您自己的接口。


### 自定义数据层
在一个 RAG 系统中，核心的是数据层。WhiskerRAG 的核心贡献是建立了数据模型，实现了 tenant、space、knowledge、task、chunk的分层机制，然后用户可以根据自己的需求定制数据层，实现抽象方法即可串联完整的知识管理流程。


### 自定义 RAG 核心流程

WhiskerRAG 提供贡献点注册机制，允许自定义核心 RAG 流程，包括资源加载(loader)、解析器(parser)、向量化(embedder)和检索策略(retriever)。
查看 `server/local_plugin/registry` 获取实现示例。

### 自定义数据处理任务
WhiskerRAG 提供自定义数据处理任务机制，允许用户根据自己的需求定制数据处理任务。
查看 `server/local_plugin/task_engine` 获取实现示例。



## 部署 📦

WhiskerRAG 支持多种部署选项，包括本地部署和 AWS 云部署。

### 私有方案部署
RAG 通常与敏感数据相关，因此私有部署是必要的。下面提供一个 基于 Docker 环境和自定义 plugin 的组合。


```bash
docker login

  # 先构建镜像
docker-compose build --no-cache
 # 后台启动服务
docker-compose up -d

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

### 使用 AWS Cloud 和 Supabase

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
API_KEY_TABLE_NAME=api_key
CHUNK_TABLE_NAME=chunk
TASK_TABLE_NAME=task
TENANT_TABLE_NAME=tenant
# LLM
OPENAI_API_KEY=your-openai-api-key
# AWS
SQS_QUEUE_URL=your-sqs-queue-url
```


## 贡献 🤝

我们欢迎贡献！请随时提交 Pull Request。

## 许可证 📄

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

⭐️ 如果您觉得这个项目有帮助，请考虑给它点个星！
