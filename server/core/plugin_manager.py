import importlib.util
import logging
import os
import sys
from typing import Union

from whiskerrag_types.interface import (
    DBPluginInterface,
    FastAPIPluginInterface,
    TaskEnginPluginInterface,
)

from .settings import settings

logger = logging.getLogger("whisker")


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
    _fastapi_plugin_module_dict = {}
    _db_plugin_instance_dict = {}
    _task_plugin_instance_dict = {}
    _fastapi_plugin_instance_dict = {}
    pluginPath = None

    @property
    def dbPlugin(self) -> Union[DBPluginInterface, None]:
        db_engine_classname = settings.DB_ENGINE_CLASSNAME
        if not self._db_plugin_module_dict:
            return None
        db_engine_instance = self._db_plugin_instance_dict.get(db_engine_classname)
        if db_engine_instance:
            return db_engine_instance
        else:
            module_class = self._db_plugin_module_dict.get(db_engine_classname)
            if module_class is None:
                raise Exception("db plugin is not found")
            db_plugin_instance = module_class(settings)
            self._db_plugin_instance_dict[db_engine_classname] = db_plugin_instance
            return db_plugin_instance

    @property
    def taskPlugin(self) -> Union[TaskEnginPluginInterface, None]:
        task_engine_classname = settings.TASK_ENGINE_CLASSNAME
        if not self._task_plugin_module_dict:
            return None
        task_engine_instance = self._task_plugin_instance_dict.get(
            task_engine_classname
        )
        if task_engine_instance:
            return task_engine_instance
        else:
            module_class = self._task_plugin_module_dict.get(task_engine_classname)
            if module_class is None:
                raise Exception("task plugin is not found")
            task_plugin_instance = module_class(settings)
            self._task_plugin_instance_dict[task_engine_classname] = (
                task_plugin_instance
            )
            return task_plugin_instance

    @property
    def fastAPIPlugin(self) -> Union[FastAPIPluginInterface, None]:
        fastapi_engine_classname = settings.FASTAPI_ENGINE_CLASSNAME
        if not self._fastapi_plugin_module_dict:
            return None
        fastapi_engine_instance = self._fastapi_plugin_instance_dict.get(
            fastapi_engine_classname
        )
        if fastapi_engine_instance:
            return fastapi_engine_instance
        else:
            module_class = self._fastapi_plugin_module_dict.get(
                fastapi_engine_classname
            )
            if module_class is None:
                return None  # fastapi plugin 可选，未找到直接返回 None
            fastapi_plugin_instance = module_class(settings)
            self._fastapi_plugin_instance_dict[fastapi_engine_classname] = (
                fastapi_plugin_instance
            )
            return fastapi_plugin_instance

    def setup_plugins(self, app):
        """设置FastAPI应用的插件相关配置（如middleware等）"""
        try:
            # 设置FastAPI插件的middleware
            fastapi_plugin = self.fastAPIPlugin
            if fastapi_plugin:
                middleware_list = fastapi_plugin.get_extra_middleware_list()
                for middleware, kwargs in middleware_list:
                    app.add_middleware(middleware, **kwargs)
                    logger.info(f"Added middleware: {middleware.__name__}")

            logger.info("Plugin setup completed successfully")
        except Exception as e:
            logger.warning(f"Plugin setup: fastapi plugin not found or error: {e}")
            logger.error(f"Error during plugin setup: {e}")
            raise

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
                    # init fastapi plugin
                    if (
                        isinstance(module_class, type)
                        and issubclass(module_class, FastAPIPluginInterface)
                        and module_class is not FastAPIPluginInterface
                    ):
                        logger.info(f"Found fastapi plugin class: {name}")
                        self._fastapi_plugin_module_dict[name] = module_class

            except Exception as e:
                logger.error(f"Failed to load plugin from '{module_path}': {e}")
                continue
