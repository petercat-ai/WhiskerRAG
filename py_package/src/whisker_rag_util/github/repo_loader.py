from typing import Optional, Union
from github import Github
from pydantic import BaseModel


class GitFileElementType(BaseModel):
    path: str
    mode: str
    url: str
    branch: str
    repo_name: str
    size: int
    file_sha: str


class GithubRepoLoader:
    repo_name: str
    branch_name: Optional[str] = None
    token: Optional[str] = None

    def __init__(
        self,
        repo_name: str,
        branch_name: Union[str, None] = None,
        token: Union[str, None] = None,
    ):
        self.repo_name = repo_name
        self.branch_name = branch_name
        self.token = token
        self.repo = None
        try:
            self._load_repo()
        except Exception as e:
            print(e)
            raise ValueError(
                f"Failed to load repo {self.repo_name} with branch {self.branch_name}."
            )

    def _load_repo(self) -> None:
        g = Github(self.token) if self.token else Github()
        self.repo = g.get_repo(self.repo_name)  # type: ignore
        if not self.branch_name and self.repo:
            self.branch_name = self.repo.default_branch

    def get_file_tree(
        self,
    ) -> list[GitFileElementType]:
        file_tree = self.repo.get_git_tree(self.branch_name, recursive=True)  # type: ignore
        file_list = []
        for item in file_tree.tree:
            if item.type == "tree":
                continue
            else:
                file_list.append(
                    GitFileElementType(
                        file_sha=item.sha,
                        path=item.path,
                        url=item.url,
                        mode=item.mode,
                        size=item.size,
                        branch=self.branch_name,  # type: ignore[arg-type]
                        repo_name=self.repo_name,
                    )
                )
        return file_list
