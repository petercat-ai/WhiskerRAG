# Whisker Server 项目配置说明

## 前置要求

- Python 3.8 或更高版本
- make 工具 (Unix/Linux/macOS 自带，Windows 需要安装)

## 快速开始

1. 克隆项目并进入目录

```bash
git clone https://github.com/petercat-ai/whiskerrag.git
cd whisker/server
```

2. 首次安装（包含所有开发依赖）

```bash
make install-dev
```

3. 启动服务器

```bash
make run
```

## 常用命令

### 基础命令

```bash
# 创建虚拟环境并安装基础依赖
make all

# 仅安装生产环境依赖
make install

# 安装所有依赖（包括开发工具）
make install-dev

# 启动开发服务器
make run
```

### 开发相关命令

```bash
# 运行测试
make test

# 格式化代码（使用 black 和 isort）
make format

# 运行类型检查
make type-check

# 清理虚拟环境和缓存文件
make clean
```

## 目录结构

```
whisker/server/
├── .venv/                 # 虚拟环境目录（自动创建）
├── tests/                 # 测试文件目录
├── main.py               # 应用入口文件
├── Makefile              # 项目管理配置文件
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
make type-check
```

### 代码格式化

使用 black 和 isort 统一代码风格：

```bash
make format
```

## 测试

运行项目测试套件：

```bash
make test
```

## 故障排除

1. 如果安装依赖失败，尝试：

```bash
make clean
make install-dev
```

2. 如果端口被占用，修改启动命令中的端口：

```bash
# 在 Makefile 中修改 run 命令
$(BIN)/uvicorn main:app --reload --port 8001
```

3. 确保 Python 版本正确：

```bash
python3 --version  # 应该 >= 3.8
```

## 注意事项

- 建议在进行任何开发之前先运行 `make install-dev`
- 提交代码前请运行 `make format` 和 `make type-check`
- 添加新依赖时，需要手动更新 Makefile 中的 install 或 install-dev 部分
