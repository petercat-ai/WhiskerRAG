from dotenv import load_dotenv, dotenv_values
import os

from whiskerrag_types.interface import SettingsInterface

load_dotenv()


class Settings(SettingsInterface):
    WEB_URL: str = os.getenv("WEB_URL")
    # table name
    KNOWLEDGE_TABLE_NAME: str = os.getenv("KNOWLEDGE_TABLE_NAME")
    CHUNK_TABLE_NAME: str = os.getenv("CHUNK_TABLE_NAME")
    TASK_TABLE_NAME: str = os.getenv("TASK_TABLE_NAME")
    ACTION_TABLE_NAME: str = os.getenv("ACTION_TABLE_NAME")
    TENANT_TABLE_NAME: str = os.getenv("TENANT_TABLE_NAME")
    # log dir
    LOG_DIR: str = os.getenv("LOG_DIR")
    # plugin env
    PLUGIN_ENV = {}
    # dev env
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
                    load_dotenv(env_path, override=True)
                    config = dotenv_values(env_path)
                    plugin_env = {**plugin_env, **config}

        self.PLUGIN_ENV = plugin_env


settings = Settings()
