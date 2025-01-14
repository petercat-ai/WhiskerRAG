#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# 导入辅助函数
source "${SCRIPT_DIR}/package.sh"

# 默认配置
PACKAGE_PATH="../py_package"
DEV_MODE="false"
FORCE_REINSTALL="false"

# 使用说明
usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -p, --path PATH    指定 package 包的路径"
    echo "  -d, --dev          安装开发依赖"
    echo "  -f, --force        强制重新安装"
    echo "  -h, --help         显示帮助信息"
    exit 1
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--path)
            PACKAGE_PATH="$2"
            shift 2
            ;;
        -d|--dev)
            DEV_MODE="true"
            shift
            ;;
        -f|--force)
            FORCE_REINSTALL="true"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            error "未知参数: $1"
            usage
            ;;
    esac
done

main() {
    # 检查必要工具
    check_requirements

    # 检查 util 包路径是否存在
    if [ ! -d "$PACKAGE_PATH" ]; then
        error "Util 包路径不存在: $PACKAGE_PATH"
        exit 1
    fi

    info "开始设置开发环境..."

    # switch to local package dir and install dependencies
    cd "$PACKAGE_PATH" || exit 1
    if [ "$DEV_MODE" = "true" ]; then
        info "安装 util 包开发依赖..."
        poetry install -E dev
    else
        info "安装 util 包基本依赖..."
        poetry install
    fi

    # back to server dir
    cd - || exit 1

    if [ "$FORCE_REINSTALL" = "true" ]; then
        info "强制重新安装 package 包..."
        poetry remove whisker-rag-util || true
    fi

    info "链接本地 package 包..."
    poetry add "${PACKAGE_PATH}"

    success "开发环境设置完成！"
}

main
