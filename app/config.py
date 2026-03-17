import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Service Account Configuration
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")

if SERVICE_ACCOUNT_FILE and os.path.exists(SERVICE_ACCOUNT_FILE):
    # Set up Vertex AI with service account
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_ACCOUNT_FILE

    # Read project ID from service account file
    with open(SERVICE_ACCOUNT_FILE, 'r') as f:
        service_account_info = json.load(f)
        project_id = service_account_info.get("project_id")
        if project_id:
            os.environ["GOOGLE_CLOUD_PROJECT"] = project_id

    os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
else:
    # Fallback to existing authentication logic
    if os.getenv("GOOGLE_API_KEY"):
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")
    else:
        import google.auth
        _, project_id = google.auth.default()
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
        os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

# Load environment variables from .env file in the app directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

@dataclass
class GeminiConfiguration:
    """Configurations for Gemini Settings"""
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model_name: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    gemini_base_url: str = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    gemini_project_id: str = os.getenv("GOOGLE_PROJECT_ID", "")
    gemini_location: str = os.getenv("GOOGLE_PROJECT_LOCATION", "")

gemini_llm_config = GeminiConfiguration()


@dataclass
class Neo4jConfiguration:
    """Configuration for Neo4j databases."""
    legal_neo4j_username: str = os.getenv("LEGAL_NEO4J_USERNAME", "")
    legal_neo4j_uri: str = os.getenv("LEGAL_NEO4J_URI", "")
    legal_neo4j_password: str = os.getenv("LEGAL_NEO4J_PASSWORD", "")
    caselaw_neo4j_uri: str = os.getenv("CASELAW_NEO4J_URI", "")
    caselaw_neo4j_username: str = os.getenv("CASELAW_NEO4J_USERNAME", "")
    caselaw_neo4j_password: str = os.getenv("CASELAW_NEO4J_PASSWORD", "")

neo4j_config = Neo4jConfiguration()


@dataclass
class OpenAIConfiguration:
    """Configuration for OpenAI API."""
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model_name: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    embeddings_model_name: str = os.getenv("OPENAI_EMBEDDINGS_MODEL_NAME")
    large_embeddings_model_name: str = os.getenv("OPENAI_LARGE_EMBEDDINGS_MODEL_NAME")

openai_config = OpenAIConfiguration()


@dataclass
class OllamaConfiguration:
    """Configuration for Ollama."""
    embeddings_model_name: str = os.getenv("OLLAMA_EMBEDDINGS_MODEL_NAME")
    host: str = os.getenv("OLLAMA_HOST")

ollama_config = OllamaConfiguration()


@dataclass
class KronMongoConfiguration:
    """Configuration for Kron Mongo databases."""
    base_url: str = os.getenv("KRON_BASE_URL")

kron_mongo_config = KronMongoConfiguration()


@dataclass
class WeaviateConfiguration:
    """Configuration for Weaviate Database."""
    http_host: str = os.getenv("WEAVIATE_HTTP_HOST", "localhost")
    http_port: str = os.getenv("WEAVIATE_HTTP_PORT", "8080")
    grpc_host: str = os.getenv("WEAVIATE_GRPC_HOST", "localhost")
    grpc_port: str = os.getenv("WEAVIATE_GRPC_PORT", "50051")
    collections_sc: str = os.getenv("COLLECTION_SC")
    collections_hc: str = os.getenv("COLLECTION_HC")
    collections_others: str = os.getenv("COLLECTION_OTHERS")

weaviate_config = WeaviateConfiguration()

@dataclass
class OpenRouterConfiguration:
    """Configuration for OpenRouter API."""
    model_name: str = os.getenv("OPENROUTER_MODELNAME")
    base_url: str = os.getenv("OPENROUTER_BASE_URL")

openrouter_config = OpenRouterConfiguration()



@dataclass
class ResearchConfiguration:
    """Configuration for research-related models and parameters.

    Attributes:
        critic_model (str): Model for evaluation tasks (legal_evaluator).
        worker_model (str): Model for working/generation tasks (researchers, composers).
        max_search_iterations (int): Maximum search iterations allowed.
    """

    critic_model: str = "gemini-2.5-flash"
    worker_model: str = "gemini-2.5-flash"
    max_search_iterations: int = 3


config = ResearchConfiguration()
