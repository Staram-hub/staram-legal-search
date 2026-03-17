from app.prompts.prompts import system_prompt_classify_user_query
from app.services.llm_service.gemini_llm import GeminiAIModel
from app.utils.get_logger import get_logger
import logging
from app.prompts.output_format_prompts import ClassifyingLegalQuery, output_format_dict, output_type_dict, legal_head_standard_output


logger = get_logger(name=__name__, level=logging.DEBUG)


async def classify_query(legal_query: str):
    """
    Classify the legal query to understand the user intent using LLM call and the output format in which the final answer would be generated.

    Args:
        legal_query (str): query to understand the user intent
    """
    llm = GeminiAIModel()

    input_type = await llm.run(
        system_prompt=system_prompt_classify_user_query,
        prompt=legal_query,
        temperature=0.0,
        response_model=ClassifyingLegalQuery,
    )
    logger.info(f"Input type for agent query runner v4: {input_type}")

    query_type = input_type.get("query_type")
    output_format_structure = None

    if query_type is not None:
        output_format_structure = output_format_dict.get(
            query_type, output_format_dict.get("2")
        )
        query_type_str = output_type_dict.get(
            query_type, output_type_dict.get("2")
        )
    else:
        query_type_str = output_type_dict.get("2") # Default if classification fails
        output_format_structure = legal_head_standard_output # Default if classification fails
    
    return {"query_type": query_type_str, "output_format": output_format_structure}
