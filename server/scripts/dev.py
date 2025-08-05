#!/usr/bin/env python3
"""
启动 Whisker 服务端的脚本
基于 VSCode launch.json 配置
"""
import os
import subprocess
import sys
import socket
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv 未安装，将跳过 .env 文件加载")
    load_dotenv = None


def is_port_available(host, port):
    """检查端口是否可用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0
    except Exception:
        return False


def find_available_port(host="127.0.0.1", start_port=8000, max_attempts=10):
    """寻找可用端口，从 start_port 开始向上递增"""
    for i in range(max_attempts):
        port = start_port + i
        if is_port_available(host, port):
            return port
    return None


def run():
    """启动服务端"""
    print("启动 Whisker 服务端...")

    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    server_dir = project_root
    plugins_dir = project_root / "supabase_aws_plugin"
    env_file = plugins_dir / ".env"

    # 检查必要的文件是否存在
    if not server_dir.exists():
        print(f"Error: 服务端目录不存在: {server_dir}", file=sys.stderr)
        sys.exit(1)

    # 加载 .env 文件
    if env_file.exists():
        if load_dotenv:
            load_dotenv(env_file)
            print(f"已加载环境变量文件: {env_file}")
        else:
            print(f"Warning: 环境配置文件存在但无法加载: {env_file}")
    else:
        print(f"Warning: 环境配置文件不存在: {env_file}")
        print("请确保已经配置了 plugins/.env 文件")

    # 设置环境变量
    env = os.environ.copy()
    env.update(
        {"WHISKER_PLUGIN_PATH": str(plugins_dir), "PYTHONPATH": str(project_root)}
    )

    # 查找可用端口
    host = "127.0.0.1"
    default_port = 8000

    # 从环境变量或命令行参数获取起始端口
    if "--port" in sys.argv:
        port_index = sys.argv.index("--port")
        if port_index + 1 < len(sys.argv):
            try:
                default_port = int(sys.argv[port_index + 1])
            except ValueError:
                print(f"Warning: 无效的端口号，使用默认端口 {default_port}")

    available_port = find_available_port(host, default_port)

    if available_port is None:
        print(
            f"Error: 无法找到可用端口（尝试范围: {default_port}-{default_port + 9}）",
            file=sys.stderr,
        )
        sys.exit(1)

    if available_port != default_port:
        print(f"端口 {default_port} 被占用，自动切换到端口 {available_port}")
    else:
        print(f"使用端口: {available_port}")

    # 构建启动命令 - 在 server 目录下运行，使用相对模块路径
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--reload",
        "--host",
        host,
        "--port",
        str(available_port),
        "--reload-dir",
        str(plugins_dir),
        "--reload-dir",
        str(server_dir),
    ]

    print(f"工作目录: {server_dir}")
    print(f"执行命令: {' '.join(cmd)}")
    print(f"服务地址: http://{host}:{available_port}")
    print("=" * 60)

    try:
        # 在 server 目录下启动，这样可以正确导入相对模块
        subprocess.run(cmd, cwd=server_dir, env=env, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: 启动服务失败: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    run()
