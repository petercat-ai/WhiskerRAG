from dotenv import load_dotenv, dotenv_values
import os

from whisker_rag_type.interface.settings_interface import SettingsInterface

# 在加载 Pydantic 设置之前加载 .env 文件
load_dotenv()


class Settings(SettingsInterface):
    WEB_URL: str = os.getenv("WEB_URL")
    # table name
    KNOWLEDGE_TABLE_NAME: str = os.getenv("KNOWLEDGE_TABLE_NAME")
    CHUNK_TABLE_NAME: str = os.getenv("CHUNK_TABLE_NAME")
    TASK_TABLE_NAME: str = os.getenv("TASK_TABLE_NAME")
    ACTION_TABLE_NAME: str = os.getenv("ACTION_TABLE_NAME")
    TENANT_TABLE_NAME: str = os.getenv("TENANT_TABLE_NAME")
    LOG_DIR: str = os.getenv("LOG_DIR")
    PLUGIN_ENV = {}
    IS_DEV: bool = os.getenv("WHISKER_ENV") == "dev"
    IS_IN_Lambda: bool = all(
        [
            os.getenv("AWS_LAMBDA_FUNCTION_NAME"),
            os.getenv("AWS_LAMBDA_FUNCTION_VERSION"),
            os.getenv("AWS_LAMBDA_RUNTIME_API"),
        ]
    )

    def load_plugin_dir_env(self, plugin_env_path: str) -> dict:
        if not plugin_env_path or not os.path.exists(plugin_env_path):
            return {}
        plugin_env = {}
        for root, _, files in os.walk(plugin_env_path):
            for file in files:
                if file.endswith(".env"):
                    env_path = os.path.join(root, file)
                    # 加载到环境变量
                    load_dotenv(env_path, override=True)
                    # 获取配置字典
                    config = dotenv_values(env_path)
                    plugin_env = {**plugin_env, **config}

        self.PLUGIN_ENV = plugin_env


settings = Settings()
