from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# 在加载 Pydantic 设置之前加载 .env 文件
load_dotenv()


class Settings(BaseSettings):
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ["true", "1", "t"]
    WEB_URL: str = os.getenv("WEB_URL")
    # table name
    KNOWLEDGE_TABLE_NAME: str = os.getenv("KNOWLEDGE_TABLE_NAME")
    CHUNK_TABLE_NAME: str = os.getenv("CHUNK_TABLE_NAME")
    TASK_TABLE_NAME: str = os.getenv("TASK_TABLE_NAME")
    ACTION_TABLE_NAME: str = os.getenv("ACTION_TABLE_NAME")
    TENANT_TABLE_NAME: str = os.getenv("TENANT_TABLE_NAME")
    LOG_DIR: str = os.getenv("LOG_DIR")


settings = Settings()
