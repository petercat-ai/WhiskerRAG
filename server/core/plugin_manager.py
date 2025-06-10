import importlib.util
import logging
import os
import sys

from whiskerrag_types.interface import DBPluginInterface, TaskEnginPluginInterface

from .log import logger
from .settings import settings


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
        db_engine_classname = settings.DB_ENGINE_CLASSNAME
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
        task_engine_classname = settings.TASK_ENGINE_CLASSNAME
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
        plugin_abs_path = os.path.abspath(plugin_dir_path)
        init_file = os.path.join(plugin_abs_path, "__init__.py")
        if not os.path.isfile(init_file):
            logger.warning(f"Missing __init__.py in: {plugin_abs_path}")
            return

        parent_dir = os.path.dirname(plugin_abs_path)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        plugin_package_name = os.path.basename(plugin_abs_path)
        try:
            self._load_module(plugin_package_name, init_file)
        except Exception as e:
            logger.error(f"Failed to load plugin package: {e}")
            return
        settings.load_plugin_dir_env(plugin_dir_path)
        plugin_files = []
        for root, _, files in os.walk(plugin_dir_path):
            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    module_path = os.path.join(root, file)
                    relative_path = os.path.relpath(module_path, plugin_dir_path)
                    depth = len(relative_path.split(os.sep))
                    plugin_files.append((depth, module_path))

        plugin_files.sort(key=lambda x: x[0])

        for _, module_path in plugin_files:
            relative_path = os.path.relpath(module_path, plugin_dir_path)
            module_name = f"{plugin_package_name}.{os.path.splitext(relative_path)[0].replace(os.sep, '.')}"
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
