from . import BaseEmbedder
from app.config import openai_config
from openai import AsyncOpenAI


class OpenAIEmbedder(BaseEmbedder):
    """
    Embedding model provided by OpenAI
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=openai_config.api_key)

    async def embed_text(self, input_text: str) -> list[float]:
        """
        Returns vector embedding of the input text

        Parameters:
            input_text (str): the text that requires embedding

        Returns (list[float]): Vector embeddings for the input text
        """

        embedding = await self.client.embeddings.create(
            input=input_text,
            model=openai_config.large_embeddings_model_name,
        )

        return embedding.data[0].embedding


class OpenLargeAIEmbedder(BaseEmbedder):
    """
    Large Embedding model provided by OpenAI
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=openai_config.api_key)

    async def embed_text(self, input_text: str) -> list[float]:
        """
        Returns vector embedding of the input text

        Parameters:
            input_text (str): the text that requires embedding

        Returns (list[float]): Vector embeddings for the input text
        """

        embedding = await self.client.embeddings.create(
            input=input_text,
            model=openai_config.large_embeddings_model_name,
        )

        return embedding.data[0].embedding
