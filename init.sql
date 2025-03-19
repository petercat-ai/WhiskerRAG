-- 启用向量扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建文档表（示例表结构）
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding VECTOR(1536)  -- 根据实际需求调整向量维度
);