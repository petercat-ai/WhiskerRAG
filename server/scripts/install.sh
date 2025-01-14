#!/bin/bash

# 检查是否在虚拟环境中
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "Virtual environment is not activated."
    
    # 检查 venv 目录是否已存在
    if [[ ! -d "venv" ]]; then
        echo "Creating new virtual environment..."
        python3 -m venv venv
    else
        echo "Virtual environment directory already exists."
    fi
    
    # 激活虚拟环境
    echo "Activating virtual environment..."
    source venv/bin/activate
    
    if [[ $? -eq 0 ]]; then
        echo "Virtual environment activated successfully."
    else
        echo "Failed to activate virtual environment."
        exit 1
    fi
else
    echo "Virtual environment is already activated: $VIRTUAL_ENV"
fi

pip3 install -r requirements.txt