#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# 信息打印函数
info() {
  echo -e "${BLUE}[INFO] $1${NC}"
}

success() {
  echo -e "${GREEN}[SUCCESS] $1${NC}"
}

error() {
  echo -e "${RED}[ERROR] $1${NC}"
}

# 检查必要工具是否安装
check_requirements() {
  if ! command -v poetry &> /dev/null; then
    error "Poetry 未安装! 请先安装 Poetry: https://python-poetry.org/docs/#installation"
    exit 1
  fi

  if ! command -v python3 &> /dev/null; then
    error "Python3 未安装!"
    exit 1
  fi
}

# 检查虚拟环境
check_virtual_env() {
  if [ -z "$VIRTUAL_ENV" ]; then
    info "未检测到虚拟环境，尝试激活虚拟环境..."
    source venv/bin/activate
    if [ -z "$VIRTUAL_ENV" ]; then
      error "未能激活虚拟环境，请手动激活虚拟环境"
      exit 1
    else
      success "虚拟环境激活成功!"
    fi
  fi
}

# 主函数
main() {
  info "开始检查必要工具..."
  check_requirements

  info "检查虚拟环境..."
  check_virtual_env

  success "所有检查通过!"
}

# 调用主函数
main
