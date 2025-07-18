import os
import platform
import subprocess
import sys


def run(cmd, shell=None):
    print(f"\033[92m$ {cmd}\033[0m")
    result = subprocess.run(cmd, shell=shell, check=True)
    return result.returncode


def ensure_poetry():
    try:
        import poetry  # noqa: F401

        print("Poetry 已安装。")
        return True
    except ImportError:
        print("Poetry 未安装，正在尝试安装...")
        try:
            run([sys.executable, "-m", "pip", "install", "poetry"])
            print("Poetry 安装成功。")
            return True
        except Exception as e:
            print(f"Poetry 安装失败: {e}")
            return False


def main():
    # 检查 poetry
    if not ensure_poetry():
        print("请手动安装 poetry 后重试。")
        sys.exit(1)
    # 配置虚拟环境目录
    run(["poetry", "config", "virtualenvs.in-project", "true"])
    # 安装依赖
    run(["poetry", "install"])
    print("\n虚拟环境和依赖已配置完成！")
    print("请使用 'poetry run run' 启动开发服务器。")


if __name__ == "__main__":
    main()
