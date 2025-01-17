from abc import ABC, abstractmethod


class SettingsInterface(ABC):
    # web console url
    WEB_URL: str
    # table name
    KNOWLEDGE_TABLE_NAME: str
    CHUNK_TABLE_NAME: str
    TASK_TABLE_NAME: str
    ACTION_TABLE_NAME: str
    TENANT_TABLE_NAME: str
    # log dir
    LOG_DIR: str
    # plugin env
    PLUGIN_ENV = dict

    @abstractmethod
    def load_plugin_dir_env(self) -> None:
        pass
