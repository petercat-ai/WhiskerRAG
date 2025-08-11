import subprocess


def run():
    subprocess.run(["black", "."])
    subprocess.run(["isort", "."])
