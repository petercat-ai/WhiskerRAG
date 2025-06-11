"""
Git configuration for AWS Lambda environment
config git environment to ensure it works in AWS Lambda
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def configure_git_environment():
    """
    configure git environment variables and paths to ensure GitPython works in AWS Lambda
    """
    try:
        # set git environment variables
        os.environ["GIT_PYTHON_REFRESH"] = "quiet"
        
        # for Docker-based Lambda, git is installed at /usr/bin/git
        git_path = "/usr/bin/git"
        if os.path.exists(git_path):
            os.environ["GIT_EXEC_PATH"] = "/usr/bin"
        else:
            # fallback to standard locations
            for path in ["/usr/bin", "/usr/local/bin", "/opt/bin"]:
                if os.path.exists(os.path.join(path, "git")):
                    os.environ["GIT_EXEC_PATH"] = path
                    break

        # ensure PATH contains git binary location
        git_exec_path = os.environ.get("GIT_EXEC_PATH", "/usr/bin")
        current_path = os.environ.get("PATH", "")
        if git_exec_path not in current_path:
            os.environ["PATH"] = f"{git_exec_path}:{current_path}"

        # set git config to avoid missing global config error
        from git import Repo

        try:
            # try to set basic git config
            os.system('git config --global user.email "petercat.assistant@gmail.com"')
            os.system('git config --global user.name "petercat whisker"')
            os.system("git config --global init.defaultBranch main")
        except Exception as e:
            logger.warning(
                f"failed to set git global config, using default config: {e}"
            )

        logger.info("git environment configured successfully")
        return True

    except Exception as e:
        logger.error(f"failed to configure git environment: {e}")
        return False


def ensure_tmp_directory():
    """
    ensure /tmp directory is writable, this is the only writable directory in Lambda
    """
    tmp_dir = Path("/tmp")
    if not tmp_dir.exists():
        tmp_dir.mkdir(parents=True, exist_ok=True)

    # create a working directory for git operations
    git_work_dir = tmp_dir / "git_repos"
    git_work_dir.mkdir(exist_ok=True)

    return str(git_work_dir)


def clone_repository(
    repo_url: str, local_path: str = None, branch: str = None, depth: int = 1
):
    """
    safely clone Git repository in AWS Lambda environment

    Args:
        repo_url: Git 仓库 URL
        local_path: local path (if None, will be created in /tmp)
        branch: branch to clone
        depth: clone depth (default is 1, shallow clone)

    Returns:
        Repo: GitPython Repo object
    """
    from git import Repo

    if not configure_git_environment():
        raise RuntimeError("failed to configure git environment")

    if local_path is None:
        work_dir = ensure_tmp_directory()
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        local_path = os.path.join(work_dir, repo_name)

    if os.path.exists(local_path):
        import shutil

        shutil.rmtree(local_path)

    try:
        logger.info(f"cloning repository {repo_url} to {local_path}")

        # build clone parameters
        clone_kwargs = {"to_path": local_path, "depth": depth}

        if branch:
            clone_kwargs["branch"] = branch

        repo = Repo.clone_from(repo_url, **clone_kwargs)
        logger.info(f"repository cloned successfully: {local_path}")
        return repo

    except Exception as e:
        logger.error(f"failed to clone repository: {e}")
        raise


def test_git_functionality():
    """
    test if git functionality works
    """
    try:
        configure_git_environment()

        # test if git command is available
        result = os.system("git --version")
        if result == 0:
            logger.info("git command test passed")
            return True
        else:
            logger.error("git command test failed")
            return False

    except Exception as e:
        logger.error(f"git functionality test failed: {e}")
        return False


if __name__ == "__main__":
    # test script
    logging.basicConfig(level=logging.INFO)

    print("testing git environment configuration...")
    if test_git_functionality():
        print("✅ git environment configured successfully")
    else:
        print("❌ git environment configuration failed")
