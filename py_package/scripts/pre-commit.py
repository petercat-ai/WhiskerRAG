#!/usr/bin/env python
import subprocess
import sys
from typing import List


def run_command(cmd: List[str]) -> int:
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError:
        return 1


def main() -> int:
    # 运行检查和格式化
    checks = [
        ["black", "."],
        ["isort", "."],
        ["pytest"],
        ["mypy"],
    ]

    for cmd in checks:
        if run_command(cmd) != 0:
            return 1

    # 执行构建
    if run_command(["poetry", "build"]) != 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
