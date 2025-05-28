# WhiskerRAG
[简体中文](README.md) | English

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![GitHub stars](https://img.shields.io/github/stars/petercat-ai/whiskerrag.svg)](https://github.com/petercat-ai/whiskerrag/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/petercat-ai/whiskerrag.svg)](https://github.com/petercat-ai/whiskerrag/issues)

A lightweight and flexible RAG (Retrieval-Augmented Generation) framework.

## Features ✨

- [**Perception**] WhiskerRAG is a lightweight RAG framework that enhances text generation through efficient information retrieval mechanisms.

- [**Flexibility**] WhiskerRAG offers a plugin architecture that enables customization of vector databases and file embedding systems, allowing users to tailor the RAG system to their specific requirements.

- [**MultiModal**] WhiskerRAG is developing a multimodal RAG system. Experience our latest features through our petercat service.

- **Coming Soon**: 
    - Web interface integration
    - enhanced knowledge retrieval capabilities 
    - knowledge graph functionalities.

## Project Structure 📁
```
.
├── server/                 # FastAPI Backend server  
│   ├── api/                # API endpoints  
│   ├── plugins/            # Plugin modules  
│   └── core/               # Core functionalities  
├── web/                    # Frontend client  
├── docker/                 # Docker images  
└── lambda_task_subscriber/ # AWS Lambda functions  
```

## Deployment 📦

WhiskerRAG supports multiple deployment options, including local and AWS cloud deployment.

### Local Deployment

Local deployment requires a Docker environment. Use the following commands:

```bash
docker login

# Build all images
docker-compose up --build -d
docker-compose up -e API_KEY=mysecretkey -e DEBUG=true -e DB_HOST=postgres

# Start all services
docker-compose start

# Stop all services
docker-compose stop

# Restart all services
docker-compose restart

# Start specific service
docker-compose start postgres

# Stop specific service
docker-compose stop postgres

# Remove all services
docker-compose down
```

Environment variables are pre-configured in `docker-compose.yml` Default values should work for most cases. For local development, refer to `.env.example` and create a `.env` file with your custom configurations.

AWS Cloud & Supabase
For enhanced system stability through cloud services, we provide AWS and Supabase integration options.
Ensure you have AWS and Supabase environments ready. Configure the environment variables in `.github/workflows/server-deploy.yml`:
```bash
TASK_ENGINE_CLASSNAME="AWSLambdaTaskEnginePlugin"
DB_ENGINE_CLASSNAME="SupaBasePlugin"
# db
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_KEY=your-supabase-service-key
# table name
KNOWLEDGE_TABLE_NAME=knowledge
API_KEY_TABLE_NAME=api_key
CHUNK_TABLE_NAME=chunk
TASK_TABLE_NAME=task
ACTION_TABLE_NAME=action
TENANT_TABLE_NAME=tenant
# llm
OPENAI_API_KEY=your-openai-api-key
# aws
SQS_QUEUE_URL=your-sqs-queue-url
```
## Advanced Usage 🚀
### Custom Data Layer
Recognizing the diverse data storage requirements in private deployments, WhiskerRAG implements a plugin mechanism for customized data storage solutions. Reference the implementation in server/local-plugin to create your own interfaces.

### Custom RAG Core Process
WhiskerRAG features a contribution point registration mechanism that allows customization of core RAG processes including resource loading, embedding, segmentation, and retrieval strategies. See `server/local-plugin-registry` for implementation examples.

## Contributing 🤝
We welcome contributions! Feel free to submit a Pull Request.

## License 📄
This project is licensed under the MIT License - see the LICENSE file for details.

⭐️ If you find this project helpful, please consider giving it a star!