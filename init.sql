CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE tenant (
    tenant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_name VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    secret_key VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE knowledge (
    knowledge_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    space_id VARCHAR(255) NOT NULL,
    knowledge_type VARCHAR(255) NOT NULL,
    knowledge_name VARCHAR(255) NOT NULL,
    source_type VARCHAR(255) NOT NULL,
    source_config JSONB NOT NULL,
    embedding_model_name VARCHAR(255) NOT NULL,
    split_config JSONB NOT NULL,
    file_sha VARCHAR(255),
    file_size INTEGER,
    metadata JSONB DEFAULT '{}',
    parent_id UUID,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    tenant_id UUID REFERENCES tenant(tenant_id)
);

CREATE TABLE chunk (
    chunk_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    space_id VARCHAR(255) NOT NULL,
    tenant_id UUID REFERENCES tenant(tenant_id),
    embedding vector,
    context TEXT NOT NULL,
    knowledge_id UUID REFERENCES knowledge(knowledge_id),
    embedding_model_name VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE task (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status VARCHAR(50) NOT NULL,
    knowledge_id UUID REFERENCES knowledge(knowledge_id),
    metadata JSONB,
    error_message TEXT,
    space_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    tenant_id UUID REFERENCES tenant(tenant_id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


-- 可以添加一些索引来优化查询性能
CREATE INDEX idx_chunk_space_id ON chunk(space_id);
CREATE INDEX idx_knowledge_space_id ON knowledge(space_id);
CREATE INDEX idx_task_space_id ON task(space_id);

-- 为 vector 列创建索引以支持向量检索
CREATE INDEX idx_chunk_embedding ON chunk USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);