import importlib.util
import os
import sys
import logging

from core.log import logger
from core.settings import settings
from whisker_rag_type.interface import TaskEnginPluginInterface, DBPluginInterface
from dotenv import load_dotenv


def singleton(cls):
    """
    单例装饰器
    """
    _instance = {}

    def _singleton(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return _singleton


@singleton
class PluginManager:
    """
    插件管理器
    1. 读取插件目录下的所有插件
    2. 检查每个插件是否实现了DBPluginInterface接口
    3. 如果实现了，则将该插件设置为当前插件
    """

    _db_plugin_list = []
    _task_plugin_list = []
    pluginPath = None

    @property
    def dbPlugin(self) -> DBPluginInterface:
        if self._db_plugin_list:
            return self._db_plugin_list[0]
        return None

    @property
    def taskPlugin(self) -> TaskEnginPluginInterface:
        if self._task_plugin_list:
            return self._task_plugin_list[0]
        return None

    def __init__(self, PluginsAbsPath=None):
        self.load_plugins(PluginsAbsPath)

    def _load_module(self, module_name, module_path):
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            logging.error(
                f"Failed to load module '{module_name}' from '{module_path}': {e}"
            )
            raise e

    def _load_env_files(directory):
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".env"):
                    env_path = os.path.join(root, file)
                    load_dotenv(env_path)
                    logger.info(f"Loaded environment variables from {env_path}")

    def load_plugins(self, pluginAbsPath):
        plugins_dir = os.path.join(pluginAbsPath, "plugins")
        self.pluginPath = plugins_dir
        logger.info(f"pluginAbsPath: {pluginAbsPath}")
        settings.load_plugin_dir_env(plugins_dir)
        for root, _, files in os.walk(plugins_dir):
            for file in files:
                if file.endswith(".py"):
                    module_path = os.path.join(root, file)
                    module_name = os.path.splitext(file)[0]
                    try:
                        module_list = self._load_module(module_name, module_path)
                        for name, module_class in module_list.__dict__.items():
                            # init db plugin
                            if (
                                isinstance(module_class, type)
                                and issubclass(module_class, DBPluginInterface)
                                and module_class is not DBPluginInterface
                            ):
                                logger.debug(f"Found db plugin class: {name}")
                                db_plugin_instance = module_class(logger, settings)
                                self._db_plugin_list.append(db_plugin_instance)
                            # init task plugin
                            if (
                                isinstance(module_class, type)
                                and issubclass(module_class, TaskEnginPluginInterface)
                                and module_class is not TaskEnginPluginInterface
                            ):
                                logger.debug(f"Found task plugin class: { name}")
                                task_plugin_instance = module_class(logger, settings)
                                self._task_plugin_list.append(task_plugin_instance)

                    except Exception as e:
                        logger.error(f"Failed to load plugin from '{module_path}': {e}")
                        continue
