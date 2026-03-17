"""
This modules provides an interface to interact with the Gemini LLM models
"""

from typing import Any
from . import AIModel
from fastapi import HTTPException
import time
from app.utils.get_logger import get_logger
import logging
import json
logger = get_logger(name=__name__, level=logging.DEBUG)
import os 
from app.config import gemini_llm_config
from google.oauth2 import service_account
from google import genai
from google.genai.types import GenerateContentConfig

class GeminiAIModel(AIModel):
    """
    This class provides an interface to interact with the Google GenAI API via Vertex AI
    using explicit Service Account credentials.
    """

    def __init__(self):

        # Service account file path from environment variable
        json_filename = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        service_account_path = os.path.join(current_dir, json_filename)

        if not os.path.exists(service_account_path):
            service_account_path = json_filename
            if not os.path.exists(service_account_path):
                raise FileNotFoundError(
                    f"Could not find service account file '{json_filename}'. "
                    f"Set the GOOGLE_SERVICE_ACCOUNT_FILE environment variable or "
                    f"place the file in {current_dir} or the project root."
                )

        try:
            # Load credentials explicitly
            creds = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            
            # Initialize the client for Vertex AI
            self.client = genai.Client(
                vertexai=True,
                project=gemini_llm_config.gemini_project_id,
                location=gemini_llm_config.gemini_location,
                credentials=creds
            ).aio
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            raise

    async def run(
        self, system_prompt: str, prompt: str, temperature: float = 0.0, **kwargs
    ) -> dict[str, Any]:
        """
        Asynchronously wait for response for input prompt
        """
        start_time = time.time()
        try:
            # 1. Prepare Configuration
            config_args = {
                "temperature": temperature,
                "system_instruction": system_prompt
            }

            # 2. Handle Structured Output (JSON)
            if "response_model" in kwargs:
                config_args["response_mime_type"] = "application/json"
                config_args["response_schema"] = kwargs["response_model"]

            config = GenerateContentConfig(**config_args)

            # 3. Make the Async Call
            response = await self.client.models.generate_content(
                model=gemini_llm_config.gemini_model_name,
                contents=prompt,
                config=config
            )

            # 4. Process Response
            if not response.candidates:
                logger.error("Gemini returned no candidates. Content might be blocked.")
                raise HTTPException(status_code=500, detail="Gemini returned no content.")

            response_text = response.candidates[0].content.parts[0].text

            if "response_model" not in kwargs:
                return {"response": response_text}
            else:
                try:
                    response_output = json.loads(response_text)
                    return response_output
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON. Raw response: {response_text}")
                    return {"parsed_response": response_text}

        except Exception as e:
            logger.error(f"Error in GeminiAIModel.run: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while processing your request to Gemini API: {e}",
            )
        finally:
            end_time = time.time()
            duration = (end_time - start_time) * 1000
            logger.info(f"Gemini LLM call duration: {duration:.2f}ms")