import asyncio
import os
from pathlib import Path
from typing import List, Optional

from langchain_community.embeddings import HuggingFaceEmbeddings
from whiskerrag_types.interface.embed_interface import BaseEmbedding, Image
from whiskerrag_types.model.knowledge import EmbeddingModelEnum
from whiskerrag_utils import RegisterTypeEnum, register

from .model_manager import HuggingFaceModelManager


@register(
    RegisterTypeEnum.EMBEDDING, EmbeddingModelEnum.PARAPHRASE_MULTILINGUAL_MINILM_L12_V2
)
class PARAPHRASE_MULTILINGUAL_MINILM_L12_V2(BaseEmbedding):
    def __init__(self):
        self.model_name = EmbeddingModelEnum.PARAPHRASE_MULTILINGUAL_MINILM_L12_V2
        self.cache_dir = os.getenv("HF_HOME", Path.home() / ".cache/huggingface")
        self.embeddings = None
        self._initialize_embeddings()

    def _initialize_embeddings(self) -> None:
        try:
            model_kwargs = {"device": "cpu"}  # cuda or cpu
            encode_kwargs = {"normalize_embeddings": True}
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs,
                cache_folder=str(self.cache_dir),
            )
        except Exception as e:
            raise Exception(f"Failed to initialize embeddings: {str(e)}")

    @classmethod
    async def _ensure_model_downloaded(cls) -> bool:
        try:
            cache_dir = os.getenv("HF_HOME", Path.home() / ".cache/huggingface")
            model_name = EmbeddingModelEnum.PARAPHRASE_MULTILINGUAL_MINILM_L12_V2
            model_manager = HuggingFaceModelManager(model_name, cache_dir)
            await model_manager.get_model_files()
            return True
        except Exception as e:
            raise Exception(f"Failed to download model: {str(e)}")

    @classmethod
    async def health_check(cls) -> bool:
        try:
            await cls._ensure_model_downloaded()

            test_text = "Health check test"
            instance = cls()
            test_embedding = await instance.embed_text(text=test_text, timeout=5)

            return isinstance(test_embedding, list) and len(test_embedding) > 0
        except Exception as e:
            print(f"Health check failed: {str(e)}")
            return False

    async def embed_text(self, text: str, timeout: Optional[int]) -> List[float]:
        timeout = timeout or 15
        loop = asyncio.get_event_loop()
        try:
            embedding = await asyncio.wait_for(
                loop.run_in_executor(None, self.embeddings.embed_query, text),
                timeout=timeout,
            )
            return embedding
        except asyncio.TimeoutError:
            raise TimeoutError(f"Embedding timed out after {timeout} seconds")

    async def embed_image(self, image: Image, timeout: Optional[int]) -> List[float]:
        raise NotImplementedError("OpenAI does not support image embedding")
