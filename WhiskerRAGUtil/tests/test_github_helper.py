import pytest
from unittest.mock import patch, MagicMock

from whisker_rag_util.github.repo_loader import GithubRepoLoader


@pytest.fixture
def mock_github():
    with patch("whisker_rag_util.github.repo_loader") as MockGithub:
        yield MockGithub


@pytest.mark.skip(reason="need to fix")
def test_get_file_tree(mock_github):
    # Arrange
    mock_repo = MagicMock()
    mock_repo.default_branch = "main"
    mock_repo.get_git_tree.return_value.tree = ["file1", "file2"]
    mock_github.return_value.get_repo.return_value = mock_repo
    mock_github._load_repo.return_value = None

    loader = GithubRepoLoader(repo_name="test_repo", branch_name="main", token="fake_token")

    # Act
    file_tree = loader.get_file_tree()

    assert file_tree == ["file1", "file2"]
    mock_github.assert_called_once_with("fake_token")
    mock_github.return_value.get_repo.assert_called_once_with("test_repo")
    mock_repo.get_git_tree.assert_called_once_with("main", recursive=True)
