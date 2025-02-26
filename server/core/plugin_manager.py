import importlib.util
import logging
import os
import sys

from core.log import logger
from core.settings import settings
from whiskerrag_types.interface import DBPluginInterface, TaskEnginPluginInterface


def singleton(cls):
    _instance = {}

    def _singleton(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return _singleton


@singleton
class PluginManager:
    _db_plugin_dict = {}
    _task_plugin_dict = {}
    pluginPath = None

    @property
    def dbPlugin(self) -> DBPluginInterface:
        if not self._db_plugin_dict:
            raise Exception("db plugin is not found")
        engine = self._db_plugin_dict.get(self.db_engine_classname)
        if not engine:
            raise Exception(
                f"db plugin {self.db_engine_classname} is not found in {list(self._db_plugin_dict.keys())}"
            )
        return engine

    @property
    def taskPlugin(self) -> TaskEnginPluginInterface:
        if not self._task_plugin_dict:
            raise Exception("task plugin is not found")
        engine = self._task_plugin_dict.get(self.task_engine_classname)
        if not engine:
            raise Exception(
                f"task plugin {self.task_engine_classname} is not found in {list(self._task_plugin_dict.keys())}"
            )
        return engine

    def __init__(self, PluginsAbsPath=None):
        self.load_plugins(PluginsAbsPath)
        self.task_engine_classname = settings.get_env("TASK_ENGINE_CLASSNAME")
        self.db_engine_classname = settings.get_env("DB_ENGINE_CLASSNAME")

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

    def load_plugins(self, pluginAbsPath):
        plugins_dir = os.path.join(pluginAbsPath, "plugins")
        if plugins_dir not in sys.path:
            sys.path.insert(0, plugins_dir)
        self.pluginPath = plugins_dir
        logger.info(f"pluginAbsPath: {plugins_dir}")
        settings.load_plugin_dir_env(plugins_dir)
        for root, _, files in os.walk(plugins_dir):
            for file in files:
                if file.endswith(".py"):
                    module_path = os.path.join(root, file)
                    relative_path = os.path.relpath(module_path, plugins_dir)
                    module_name = os.path.splitext(relative_path)[0].replace(
                        os.sep, "."
                    )
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
                                self._db_plugin_dict[name] = db_plugin_instance
                            # init task plugin
                            if (
                                isinstance(module_class, type)
                                and issubclass(module_class, TaskEnginPluginInterface)
                                and module_class is not TaskEnginPluginInterface
                            ):
                                logger.debug(f"Found task plugin class: { name}")
                                task_plugin_instance = module_class(logger, settings)
                                self._task_plugin_dict[name] = task_plugin_instance

                    except Exception as e:
                        logger.error(f"Failed to load plugin from '{module_path}': {e}")
                        continue
