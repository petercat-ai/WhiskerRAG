## 项目启动

全局安装 poetry

```bash
pip install poetry
```

然后在项目根目录下执行以下命令管理依赖

```bash
# 安装所有依赖
poetry install

# 添加新依赖
poetry add requests
poetry add pytest --group dev

# 更新依赖
poetry update

# 移除依赖
poetry remove requests
```

## 本地测试

```bash
# 运行测试
poetry run pytest

# 带覆盖率报告
poetry run pytest --cov

# 查看HTML格式的覆盖率报告
poetry run pytest --cov --cov-report=html
open htmlcov/index.html

```

# 构建并发布

```bash
poetry run build

poetry publish
```
