import pytest
import sys
import os

# 添加源代码目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 定义全局 fixtures
@pytest.fixture
def setup_data():
    # 设置测试数据
    data = {"key": "value"}
    return data
