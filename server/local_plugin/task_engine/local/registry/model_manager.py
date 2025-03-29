import os
from pathlib import Path
from typing import Optional
from functools import partial
import asyncio
import logging
from huggingface_hub import snapshot_download, HfApi
from huggingface_hub.utils import LocalEntryNotFoundError, RepositoryNotFoundError


class HuggingFaceModelManager:
    """Hugging Face 模型管理器"""

    def __init__(
        self, model_name: str, cache_dir: Optional[Path] = None, revision: str = "main"
    ):
        self.model_name = model_name
        self.cache_dir = cache_dir or Path(
            os.getenv("HF_HOME", Path.home() / ".cache/huggingface")
        )
        self.revision = revision
        self.api = HfApi()
        self.logger = logging.getLogger(__name__)

    @property
    def model_path(self) -> Path:
        org, model = self.model_name.split("/")
        cache_path = self.cache_dir / f"models--{org}--{self.model_name}"
        return cache_path / "snapshots" / self.revision

    def is_model_cached(self) -> bool:
        try:
            model_path = self.model_path
            # 检查模型文件是否存在且完整
            if not model_path.exists():
                return False

            # 检查关键文件是否存在（根据具体模型类型可能需要调整）
            required_files = ["config.json", "pytorch_model.bin"]
            return all((model_path / file).exists() for file in required_files)
        except Exception as e:
            self.logger.warning(f"Error checking model cache: {e}")
            return False

    async def ensure_model_downloaded(
        self, force_download: bool = False, local_files_only: bool = False
    ) -> Path:
        """
        确保模型已下载到本地

        Args:
            force_download: 是否强制重新下载
            local_files_only: 是否只使用本地文件

        Returns:
            Path: 模型本地路径
        """
        try:
            # 如果不强制下载且模型已缓存，直接返回
            if not force_download and self.is_model_cached():
                self.logger.info(f"Model {self.model_name} found in cache")
                return self.model_path

            # 准备下载参数
            download_kwargs = {
                "repo_id": self.model_name,
                "cache_dir": str(self.cache_dir),
                "local_files_only": local_files_only,
                "force_download": force_download,
                "revision": self.revision,
            }

            # 异步下载
            loop = asyncio.get_event_loop()
            download_func = partial(snapshot_download, **download_kwargs)
            model_path = await loop.run_in_executor(None, download_func)

            self.logger.info(f"Model downloaded to {model_path}")
            return Path(model_path)

        except LocalEntryNotFoundError:
            if local_files_only:
                raise ValueError(f"Model {self.model_name} not found in local cache")
            raise
        except RepositoryNotFoundError:
            raise ValueError(f"Model {self.model_name} not found on Hugging Face Hub")
        except Exception as e:
            raise RuntimeError(f"Failed to download model: {str(e)}")

    async def get_model_files(self) -> Path:
        """
        获取模型文件路径，如果需要则下载
        """
        try:
            # 首先尝试使用本地文件
            try:
                return await self.ensure_model_downloaded(local_files_only=True)
            except ValueError:
                # 本地没有找到，尝试下载
                return await self.ensure_model_downloaded(local_files_only=False)
        except Exception as e:
            self.logger.error(f"Failed to get model files: {e}")
            raise
