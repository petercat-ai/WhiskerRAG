"""
This file was originally sourced from the https://github.com/langchain-ai/langchain/blob/master/libs/community/langchain_community/document_loaders/github.py
and it has been modified based on the requirements provided by petercat.
"""

import base64
from typing import Callable, Optional
from github import Github
from langchain_core.documents import Document

from .repo_loader import GitFileElementType


class GithubFileLoader:
    repo_name: str
    github: Github
    file_path: str
    branch: str
    commit_id: str
    file_sha: str
    github_api_url: str = "https://api.github.com"
    token: Optional[str]
    file_size: int = 0
    file_element: GitFileElementType

    def __init__(
        self,
        file_element: GitFileElementType,
        token: Optional[str] = None,
        commit_id: Optional[str] = None,
    ):
        self.file_element = file_element
        self.repo_name = file_element.repo_name
        self.file_path = file_element.path
        self.branch = file_element.branch
        self.github = Github(self.repo_name, token)
        if not commit_id:
            self.commit_id = self._get_commit_id_by_branch(self.branch)
        else:
            self.commit_id = commit_id

    def _get_commit_id_by_branch(self, branch: str) -> str:
        repo = self.github.get_repo(self.repo_name)
        branch_info = repo.get_branch(branch)
        return branch_info.commit.sha

    def get_file_content_by_path(self, path: str) -> str:
        repo = self.github.get_repo(self.repo_name)
        file_content = (
            repo.get_contents(path, ref=self.commit_id)
            if self.commit_id
            else repo.get_contents(path)
        )
        if isinstance(file_content, list):
            print("[warn]file_content is a list")
            file_content = file_content[0]
        self.file_sha = file_content.sha
        self.file_size = file_content.size
        return base64.b64decode(file_content.content).decode("utf-8")

    def load(self) -> Document:
        content = self.get_file_content_by_path(self.file_path)
        metadata = {
            **self.file_element.model_dump(),
            "commit_id": self.commit_id,
            "file_sha": self.file_sha,
        }
        return Document(page_content=content, metadata=metadata)
