import os

from dotenv import dotenv_values, load_dotenv
from whiskerrag_types.interface import SettingsInterface

# load main env first
load_dotenv()


class Settings(SettingsInterface):
    @property
    def WEB_URL(self) -> str:
        return os.getenv("WEB_URL", "")

    @property
    def KNOWLEDGE_TABLE_NAME(self) -> str:
        return os.getenv("KNOWLEDGE_TABLE_NAME", "")

    @property
    def CHUNK_TABLE_NAME(self) -> str:
        return os.getenv("CHUNK_TABLE_NAME", "")

    @property
    def TASK_TABLE_NAME(self) -> str:
        return os.getenv("TASK_TABLE_NAME", "")

    @property
    def ACTION_TABLE_NAME(self) -> str:
        return os.getenv("ACTION_TABLE_NAME", "")

    @property
    def TENANT_TABLE_NAME(self) -> str:
        return os.getenv("TENANT_TABLE_NAME", "")

    @property
    def PLUGIN_PATH(self) -> str:
        return os.getenv("WHISKER_PLUGIN_PATH", "./plugins")

    # log dir
    @property
    def LOG_DIR(self) -> str:
        return os.getenv("LOG_DIR", "./logs")

    # dev env
    @property
    def IS_DEV(self) -> str:
        return os.getenv("WHISKER_ENV") == "dev"

    # plugin env
    PLUGIN_ENV: dict = {}

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
        for root, _, files in os.walk(plugin_env_path):
            for file in files:
                if file.endswith(".env"):
                    env_path = os.path.join(root, file)
                    load_dotenv(env_path, override=True)
                    env_dict = dotenv_values(env_path)
                    self.PLUGIN_ENV.update(env_dict)
        return self.PLUGIN_ENV

    def get_env(self, name, default_value=None):
        return os.getenv(name) or default_value


settings = Settings()
