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
    _db_plugin_module_dict = {}
    _task_plugin_module_dict = {}
    _db_plugin_instance_dict = {}
    _task_plugin_instance_dict = {}
    pluginPath = None

    @property
    def dbPlugin(self) -> DBPluginInterface:
        db_engine_classname = settings.get_env("DB_ENGINE_CLASSNAME")
        if not self._db_plugin_module_dict:
            raise Exception("db plugin is not found")
        db_engine_instance = self._db_plugin_instance_dict.get(db_engine_classname)
        if db_engine_instance:
            return db_engine_instance
        else:
            module_class = self._db_plugin_module_dict.get(db_engine_classname)
            db_plugin_instance = module_class(logger, settings)
            self._db_plugin_instance_dict[db_engine_classname] = db_plugin_instance
            return db_plugin_instance

    @property
    def taskPlugin(self) -> TaskEnginPluginInterface:
        task_engine_classname = settings.get_env("TASK_ENGINE_CLASSNAME")
        if not self._task_plugin_module_dict:
            raise Exception("task plugin is not found")
        task_engine_instance = self._task_plugin_instance_dict.get(
            task_engine_classname
        )
        if task_engine_instance:
            return task_engine_instance
        else:
            module_class = self._task_plugin_module_dict.get(task_engine_classname)
            task_plugin_instance = module_class(logger, settings)
            self._task_plugin_instance_dict[task_engine_classname] = (
                task_plugin_instance
            )
            return task_plugin_instance

    def __init__(self, Plugin_dir_abs_path=None):
        self._load_plugins(Plugin_dir_abs_path)

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

    def _load_plugins(self, plugin_dir_path):
        if plugin_dir_path not in sys.path:
            sys.path.insert(0, plugin_dir_path)
        self.pluginPath = plugin_dir_path
        logger.info(f"pluginAbsPath: {plugin_dir_path}")
        settings.load_plugin_dir_env(plugin_dir_path)
        for root, _, files in os.walk(plugin_dir_path):
            for file in files:
                if file.endswith(".py"):
                    module_path = os.path.join(root, file)
                    relative_path = os.path.relpath(module_path, plugin_dir_path)
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
                                logger.info(f"Found db plugin class: {name}")
                                self._db_plugin_module_dict[name] = module_class
                            # init task plugin
                            if (
                                isinstance(module_class, type)
                                and issubclass(module_class, TaskEnginPluginInterface)
                                and module_class is not TaskEnginPluginInterface
                            ):
                                logger.info(f"Found task plugin class: { name}")
                                self._task_plugin_module_dict[name] = module_class

                    except Exception as e:
                        logger.error(f"Failed to load plugin from '{module_path}': {e}")
                        continue
