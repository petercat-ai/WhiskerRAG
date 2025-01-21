#!/bin/bash

# 检查 poetry 是否安装
if ! command -v poetry &> /dev/null
then
  echo "Poetry 未安装，正在安装..."
  curl -sSL https://install.python-poetry.org | python3 -
  export PATH="$HOME/.local/bin:$PATH"
else
  echo "Poetry 已安装"
fi

# 删除 lock 文件
rm -f poetry.lock

# 安装依赖，忽略 lock 文件
poetry install --no-root

# 激活 poetry 虚拟环境
source $(poetry env info --path)/bin/activate

# 检查 pip 版本，并强制升级到最新
pip install --upgrade pip

# 安装 ./plugins 目录下 requirements.txt 中的依赖
pip install -r ./plugins/requirements.txt

# 启动 FastAPI 应用
uvicorn main:app --host 0.0.0.0 --port 8000