import importlib.util
import logging
import os
import sys
import ast
from typing import Union, Dict, Set, List
from collections import defaultdict

from whiskerrag_types.interface import (
    DBPluginInterface,
    TaskEnginPluginInterface,
    FastAPIPluginInterface,
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


class CircularDependencyError(Exception):
    """Circular dependency detection exception"""

    def __init__(self, cycle_path: List[str]):
        self.cycle_path = cycle_path
        super().__init__(f"Circular dependency detected: {' -> '.join(cycle_path)}")


class DependencyAnalyzer:
    """Dependency analyzer for detecting circular imports"""

    def __init__(self, plugin_root_path: str):
        self.plugin_root_path = os.path.abspath(plugin_root_path)
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.module_files: Dict[str, str] = {}

    def analyze_file_imports(self, file_path: str) -> Set[str]:
        """Analyze imports in a Python file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            imports = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
                        # Also add submodule imports
                        for alias in node.names:
                            if alias.name != "*":
                                imports.add(f"{node.module}.{alias.name}")

            return imports
        except Exception as e:
            logger.warning(f"Failed to analyze imports in {file_path}: {e}")
            return set()

    def build_dependency_graph(self, plugin_package_name: str):
        """Build dependency graph for all Python files in the plugin"""
        # Collect all Python files
        for root, _, files in os.walk(self.plugin_root_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.plugin_root_path)

                    # Convert file path to module name
                    if file == "__init__.py":
                        module_parts = relative_path.split(os.sep)[:-1]
                    else:
                        module_parts = os.path.splitext(relative_path)[0].split(os.sep)

                    if module_parts and module_parts != [""]:
                        module_name = f"{plugin_package_name}.{'.'.join(module_parts)}"
                    else:
                        module_name = plugin_package_name

                    self.module_files[module_name] = file_path

        # Analyze dependencies for each module
        for module_name, file_path in self.module_files.items():
            imports = self.analyze_file_imports(file_path)

            # Filter imports to only include modules within the plugin
            for imported_module in imports:
                if imported_module.startswith(plugin_package_name):
                    # Normalize the imported module name
                    if imported_module in self.module_files:
                        self.dependencies[module_name].add(imported_module)
                    else:
                        # Try to find the closest matching module
                        for existing_module in self.module_files:
                            if imported_module.startswith(existing_module):
                                self.dependencies[module_name].add(existing_module)
                                break

    def detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies using DFS"""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node: str, path: List[str]) -> bool:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return True

            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.dependencies.get(node, set()):
                if dfs(neighbor, path):
                    return True

            rec_stack.remove(node)
            path.pop()
            return False

        for module in self.module_files:
            if module not in visited:
                dfs(module, [])

        return cycles


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
                raise Exception(f"can not find db plugin: {db_engine_classname}")
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
                raise Exception("fastapi plugin is not found")
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
            logger.error(f"Error during plugin setup: {e}")
            raise

    def __init__(self, plugin_path=None):
        """Initialize PluginManager with specified plugin path"""
        if plugin_path is None:
            # Use a relative path that works from the server directory
            plugin_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "plugins"
            )

        self.pluginPath = plugin_path
        self._load_plugins_from_directory(plugin_path)

    def _load_module_safe(self, module_name: str, module_path: str):
        """Safely load a module with error handling"""
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot create spec for module {module_name}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            logger.error(
                f"Failed to load module '{module_name}' from '{module_path}': {e}"
            )
            # Remove from sys.modules if it was added
            if module_name in sys.modules:
                del sys.modules[module_name]
            raise e

    def _detect_and_handle_circular_dependencies(
        self, plugin_dir_path: str, plugin_package_name: str
    ):
        """Detect circular dependencies and handle them"""
        analyzer = DependencyAnalyzer(plugin_dir_path)
        analyzer.build_dependency_graph(plugin_package_name)
        cycles = analyzer.detect_cycles()

        if cycles:
            logger.error("Circular dependency detected in plugin loading!")
            for i, cycle in enumerate(cycles):
                cycle_path = " -> ".join(cycle)
                logger.error(f"Circular dependency path {i+1}: {cycle_path}")
                print(
                    f"ERROR: Circular dependency detected in plugin '{plugin_package_name}'"
                )
                print(f"Dependency cycle {i+1}: {cycle_path}")

            raise CircularDependencyError(cycles[0])

        logger.info(
            f"No circular dependencies detected in plugin '{plugin_package_name}'"
        )

    def _load_plugins_from_directory(self, plugin_path: str):
        """Load all plugins from the specified directory"""
        if not os.path.exists(plugin_path):
            logger.warning(f"Plugin directory does not exist: {plugin_path}")
            return

        # Add plugin directory to sys.path so we can import plugin packages directly
        plugin_abs_path = os.path.abspath(plugin_path)
        if plugin_abs_path not in sys.path:
            sys.path.insert(0, plugin_abs_path)

        # Scan for plugin directories
        for item in os.listdir(plugin_path):
            item_path = os.path.join(plugin_path, item)
            if os.path.isdir(item_path) and not item.startswith("."):
                init_file = os.path.join(item_path, "__init__.py")
                if os.path.isfile(init_file):
                    try:
                        self._load_single_plugin(item_path, item)
                    except Exception as e:
                        logger.error(f"Failed to load plugin '{item}': {e}")
                        continue

    def _load_single_plugin(self, plugin_dir_path: str, plugin_package_name: str):
        """Load a single plugin using standard Python import mechanism"""
        logger.info(f"Loading plugin: {plugin_package_name}")

        # Load plugin environment settings
        settings.load_plugin_dir_env(plugin_dir_path)

        try:
            # Use standard Python import to load the entire plugin package
            # This allows the package's __init__.py to control what gets loaded
            plugin_module = importlib.import_module(plugin_package_name)

            # Scan the main plugin module for plugin classes
            self._scan_module_for_plugins(plugin_module)

            # Also scan any explicitly imported submodules that are available
            # This only scans modules that were actually imported by the package
            self._scan_imported_submodules(plugin_module, plugin_package_name)

            logger.info(f"Successfully loaded plugin: {plugin_package_name}")

        except Exception as e:
            logger.error(f"Failed to load plugin package '{plugin_package_name}': {e}")
            return

    def _scan_imported_submodules(self, plugin_module, plugin_package_name: str):
        """Scan submodules that were imported by the plugin package"""
        import sys

        # Get all modules that start with the plugin package name
        plugin_modules = [
            (name, module)
            for name, module in sys.modules.items()
            if name.startswith(plugin_package_name + ".") and module is not None
        ]

        # Scan each imported submodule for plugin classes
        for module_name, module in plugin_modules:
            try:
                self._scan_module_for_plugins(module)
            except Exception as e:
                logger.warning(f"Error scanning module {module_name}: {e}")
                continue

    def _scan_module_for_plugins(self, module):
        """Scan a module for plugin classes and register them"""
        for name, module_class in module.__dict__.items():
            try:
                # Check for DB plugin
                if (
                    isinstance(module_class, type)
                    and issubclass(module_class, DBPluginInterface)
                    and module_class is not DBPluginInterface
                ):
                    logger.info(f"Found db plugin class: {name}")
                    self._db_plugin_module_dict[name] = module_class

                # Check for Task plugin
                elif (
                    isinstance(module_class, type)
                    and issubclass(module_class, TaskEnginPluginInterface)
                    and module_class is not TaskEnginPluginInterface
                ):
                    logger.info(f"Found task plugin class: {name}")
                    self._task_plugin_module_dict[name] = module_class

                # Check for FastAPI plugin
                elif (
                    isinstance(module_class, type)
                    and issubclass(module_class, FastAPIPluginInterface)
                    and module_class is not FastAPIPluginInterface
                ):
                    logger.info(f"Found fastapi plugin class: {name}")
                    self._fastapi_plugin_module_dict[name] = module_class

            except Exception as e:
                logger.warning(f"Error checking class {name}: {e}")
                continue
