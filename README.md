# WhiskerRAG
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/petercat-ai/whiskerrag.svg)](https://github.com/petercat-ai/whiskerrag/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/petercat-ai/whiskerrag.svg)](https://github.com/petercat-ai/whiskerrag/issues)

A lightweight and flexible RAG (Retrieval-Augmented Generation) framework.

## Features ✨

- [**Perception**] WhiskerRAG is a lightweight RAG (Retrieval-Augmented Generation) framework that enhances text generation through efficient information retrieval.

- [**Flexibility**] WhiskerRAG enables customization of vector databases and file embedding systems through a plugin architecture, allowing users to tailor the RAG system to their specific needs.

- [**MultiModal**] WhiskerRAG 正在打造一个支持多模态场景的 RAG 系统。你可以在我们的 petercat 服务中体验到最新的系统。

## Project Structure 📁
```
├── server/       # FastAPI Backend server
    ├── api/      # API endpoints
    ├── plugins/  # Plugin modules
    ├── core/     # Core functionalities
├── web/      # Frontend client
├── docker/   # Docker images
└── lambda_task_subscriber/ # AWS Lambda functions
```

## Deploy 📦
whisker 支持多种部署方式，包括本地部署，亚马逊云部署。
### Local

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

### AWS Cloud & supabase
请提前准备好 aws 环境和 supabase 环境
```bash
# Install AWS SAM CLI
python3 -m pip install aws-sam-cli

# Verify installation
sam --version
```

## Plugin
我们注意到在私有化部署时，大家对数据存储方案个性化需求较为强烈。因此 WhiskerRAG 提供了插件机制，允许用户自定义数据存储方案。参考
文件夹 `server/plugins`内的写法，用户需要自行实现相关的接口。同时在部署时需要更改相关环境变量。


## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

⭐️ If you find this project useful, please consider giving it a star!
