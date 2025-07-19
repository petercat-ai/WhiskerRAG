# Whisker Server 项目配置说明

## 前置要求

- Python 3.11 或更高版本
- 推荐使用 Poetry 进行依赖和虚拟环境管理

## 快速开始

1. 克隆项目并进入目录

```bash
git clone https://github.com/petercat-ai/whiskerrag.git
cd whisker/server
```

2. 安装 Poetry

```bash
pip install poetry
```

3. （强烈建议首次执行）配置虚拟环境目录为 .venv

```bash
poetry config virtualenvs.in-project true
```

4. 安装依赖

```bash
poetry install
```

5. 启动服务器

```bash
poetry run run
```

> 💡 你也可以直接运行一键初始化脚本 `python init.py`，自动完成上述 3-4 步骤。

## 常用命令

### 基础命令

```bash
# 安装依赖
poetry install

# 启动开发服务器
poetry run run
```

### 插件依赖管理

如需使用 plugins 目录下的插件功能，请按需安装插件依赖：

- 一键安装插件依赖：
  poetry run pip install -r plugins/requirements.txt
- 一键卸载插件依赖：
  poetry run pip uninstall -r plugins/requirements.txt
- （可选）单独安装某个插件依赖：
  poetry run pip install supabase boto3

建议仅在需要时安装插件依赖，避免污染主环境。

### 开发相关命令

```bash
# 运行测试
poetry run test

# 格式化代码（使用 black 和 isort）
poetry run format

# 运行类型检查
poetry run type-check
```

## 目录结构

```
whisker/server/
├── .venv/                 # 虚拟环境目录（自动创建）
├── tests/                 # 测试文件目录
├── main.py               # 应用入口文件
├── pyproject.toml        # Poetry 配置文件
```

## 开发环境配置

### 虚拟环境

项目使用 Python 虚拟环境来隔离依赖。虚拟环境会自动创建在 `.venv` 目录下。

### 依赖管理

- 生产环境依赖包括：fastapi, uvicorn, pydantic 等
- 开发环境依赖包括：pytest, black, isort, mypy 等

## 代码规范

### 类型检查

使用 mypy 进行静态类型检查：

```bash
poetry run type-check
```

### 代码格式化

使用 black 和 isort 统一代码风格：

```bash
poetry run format
```

## 测试

运行项目测试套件：

```bash
poetry run test
```

## 故障排除

1. 如果安装依赖失败，尝试：

```bash
poetry install --no-root
```

2. 如果端口被占用，修改启动命令中的端口：

```bash
# 修改 pyproject.toml 或 main.py 中的端口配置
```

3. 确保 Python 版本正确：

```bash
python3 --version  # 应该 >= 3.11
```

## 注意事项

- 建议在进行任何开发之前先运行 `poetry install`
- 提交代码前请运行 `poetry run format` 和 `poetry run type-check`
- 添加新依赖时，使用 `poetry add` 或 `poetry add --group dev` 管理
- CI/CD 环境下请确保 Python 版本 >=3.11，且 server/README.md 文件存在，否则 poetry install 会报错
