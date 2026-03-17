from google.adk.tools import ToolContext
from app.services.neo4j_connection_pool import get_neo4j_client
from app.services.weaviate_database import get_weaviate_db
from app.services.llm_service.openai_embedder import OpenLargeAIEmbedder
from app.data.graph_data import court_names

from app.config import neo4j_config
from app.prompts.cypher_queries import (
    cypher_query_get_caselaw_schema,
    cypher_query_retrieve_cases_connected_to_sections,
    cypher_query_retrieve_cases_from_ids,
    cypher_query_retrieve_cases_analysis_from_ids,
)
from typing import Any

from app.utils.get_logger import get_logger
import logging

logger = get_logger(name=__name__, level=logging.DEBUG)

async def get_caselaw_schema() -> list[dict[str, Any]]:
    """
    Get the schema of the caselaw database.

    Returns:
        list[dict[str,Any]]: The schema of the caselaw database.
    """
    logger.debug("running get_caselaw_schema")

    neo4j_client = get_neo4j_client(
        uri=neo4j_config.caselaw_neo4j_uri,
        user=neo4j_config.caselaw_neo4j_username,
        password=neo4j_config.caselaw_neo4j_password,
    )

    schema_result = await neo4j_client.run_query(cypher_query_get_caselaw_schema)
    return schema_result


async def get_caselaw_nodes(cypher_query: str) -> list[dict[str, Any]]:
    """
    Get the nodes from the caselaw database based on the provided cypher query.

    Args:
        cypher_query (str): The cypher query to run on the caselaw database.

    Returns:
        list[dict[str, Any]]: The nodes retrieved from the caselaw database based on the cypher query.
    """

    neo4j_client = get_neo4j_client(
        uri=neo4j_config.caselaw_neo4j_uri,
        user=neo4j_config.caselaw_neo4j_username,
        password=neo4j_config.caselaw_neo4j_password,
    )

    caselaw_nodes_result = await neo4j_client.run_query(
        query=cypher_query,
        timeout=120
        )
    return caselaw_nodes_result


# --------------------------- V2 CaseLaw Retrieval ---------------------


async def get_court_names() -> list[str]:
    """
    This tool returns all the court names present in the caselaw database
    Returns:
        list[str]: List of court names present in the caselaw database
    """
    logger.debug("Agent retrieving all court names")
    return court_names


async def get_caselaw_from_weaviate(
    similarity_type: str,
    keywords: str,
    section_ids: list[str] | None = None,
    courts: list[str] | None = None,
    benchcoram_size: int | None = None,
):
    """
    Retrieves caselaws from neo4j/weviate in a 2 step process.
    1. Given section ids (ids relative to neo4j), retrieve cases that have referred or influenced that
        section (under an Act). If section ids is None, retrieve all cases from neo4j
    2. Provided keywords (seperated by commas), we then retrieve the top k(=5) caselaws
        from the cases retrieved in step 1, that are semantically most similar to the keywords.

    Args:
        similarity_type (str): This refers to what component of a case do you want to be similar to. Can
            occupy only from the following values: ['Rules', 'Facts', 'Issues', 'Analysis', 'Conclusion'].
            For any other value, this variable will be set to 'Facts' by default
        keywords (str): A comma-separated string of keywords to find relevant caselaws to answer user query
        section_ids (list[str] | None): List of section ids (neo4j ids) to find relevant caselaws that have
            referred or influenced that section. If None, retrieve all cases from neo4j
        court (list[str] | None): List of courts to filter the cases by. If None, no filtering is done.
            Remember that the court name should match in database exactly, for this use the `get_court_names`
            tool
        benchcoram_size (int | None): Minimum benchcoram size to filter the cases by. If None, no filtering



    Returns:
        Caselaws
    """
    valid_similarity_types = ["Rules", "Facts", "Issues", "Analysis", "Conclusion"]
    if similarity_type not in valid_similarity_types:
        logger.warning(f"Invalid similarity_type '{similarity_type}' received. Must be one of {valid_similarity_types}. Defaulting to 'Facts'.")
        similarity_type = "Facts"

    logger.debug(f"Caselaw Keywords: {keywords}")
    logger.debug(f"Similarity Type: {similarity_type}")

    embedder = OpenLargeAIEmbedder()
    weaviate_database = get_weaviate_db()

    embed_query = await embedder.embed_text(keywords)

    neo4j_client = get_neo4j_client(
        uri=neo4j_config.legal_neo4j_uri,
        user=neo4j_config.legal_neo4j_username,
        password=neo4j_config.legal_neo4j_password,
    )
    if courts is not None:
        courts = [court.lower() for court in courts]

    if section_ids is None:
        logger.debug("sections is None")
        cases_connected_to_sections = await neo4j_client.run_query(
            query=cypher_query_retrieve_cases_from_ids,
            parameters={
                "BenchValue": benchcoram_size,
                "Court": courts,
            },
        )

    else:
        logger.debug("Running with section_ids")
        logger.info(
            f"All inputs: {keywords}, {section_ids}, {similarity_type}, {courts}, {benchcoram_size}"
        )
        cases_connected_to_sections = await neo4j_client.run_query(
            query=cypher_query_retrieve_cases_connected_to_sections,
            parameters={
                "section_ids": section_ids,
                "BenchValue": benchcoram_size,
                "Court": courts,
            },
        timeout=120
        )

    cases_dict: dict[str, Any] = {}
    # logger.info(cases_connected_to_sections)

    if cases_connected_to_sections == []:
        return [
            f"No cases were found for inputs keywords: {keywords}, section_ids: {section_ids},\
            similarity_type: {similarity_type}, courts: {courts}, bechcoram size: {benchcoram_size}"
        ]

    for case in cases_connected_to_sections:
        cases_dict[case.get("case_id", "temp")] = {
            "case_analysis": case.get(
                "case_analysis", "No Analysis found for this case"
            ),
            "case_conclusion": case.get(
                "case_conclusion", "No Case conclusion found for this case"
            ),
        }

        if section_ids is not None:
            cases_dict[case.get("case_id", "temp")] = {
                "relevant_sections_referred_by_the_case": [
                    case.get("refers_to_sections", [])
                ]
            }

    cases_returned: list[str] = [key for key in cases_dict]

    top_cases_relevant_to_keywords = await weaviate_database.search_similar_content_in_specific_cases(
        case_ids=cases_returned,
        query_embedding=embed_query,
        similarity_type=similarity_type,
    )

    output = []
    keys = ["iLOCaseNo", "content", "court"]

    for o in top_cases_relevant_to_keywords.objects:
        case_dict: dict[str, Any] = {"type": similarity_type}
        current_case_id = o.properties.get("iLOCaseNo")

        for key in keys:
            case_dict[key] = o.properties.get(key)
        case_dict["case_analysis"] = cases_dict.get(current_case_id, {}).get(
            "case_analysis", "No Case Analysis found for this case"
        )
        case_dict["case_conclusion"] = cases_dict.get(current_case_id, {}).get(
            "case_conclusion", "No Case conclusion found for this case"
        )

        output.append(case_dict)

    return output


async def get_caselaw_per_section(
    keywords: str,
    section_ids: list[str],
    similarity_type: str,
    courts: list[str],
    benchcoram_size: int,
    tool_context: ToolContext,
) -> list[dict[str, Any]]:
    """
    Given section ids (from neo4j), retrieve cases that have referred or influenced those sections.
    Then uses semantic similarity to find the top k(=5) most relevant cases matching the search query.

    Arg:
        keywords (str): A descriptive search sentence capturing the legal essence of the query.
            Example: "Validity of unregistered sale deed for immovable property under Transfer of Property Act"
            This gets embedded and matched semantically against case law FIRAC components.
        section_ids (list[str]): List of section ids (neo4j ids) to find relevant caselaws that have
            referred or influenced that section
        similarity_type (str): Which FIRAC component to search against. MUST be exactly one of:
            ['Rules', 'Facts', 'Issues', 'Analysis', 'Conclusion'].
            Choose based on query intent — do NOT always default to 'Facts'.
        courts (list[str]): List of courts to filter the cases by. If None, no filtering is done.
            Court names must match exactly — use `get_court_names` tool to get valid names.
        benchcoram_size (int): Minimum bench/coram size to filter cases by. Default value is 0.
            Filtering is done by >= comparison.

    Returns:
        list[dict[str, Any]]: List of relevant cases with their analysis, conclusion, court, and
            section references, in order of relevance.
    """
    court_value = courts
    benchcoram_size_value = benchcoram_size
    logger.warning(
        f"Inputs are: {keywords}, {section_ids}, {similarity_type}, {courts}, {benchcoram_size}"
    )

    if courts == []:
        court_value = None
    if benchcoram_size == 0:
        benchcoram_size_value = None

    result = await get_caselaw_from_weaviate(
        similarity_type=similarity_type,
        keywords=keywords,
        section_ids=section_ids,
        courts=court_value,
        benchcoram_size=benchcoram_size_value,
    )

    # Write results directly to state for downstream agents (composer)
    existing = tool_context.state.get("caselaw_section_data", [])
    if isinstance(result, list):
        existing.extend(result)
    tool_context.state["caselaw_section_data"] = existing
    logger.debug(f"Wrote {len(result) if isinstance(result, list) else 0} cases to state['caselaw_section_data']")

    return result


async def get_caselaw_per_keyword_only(
    keywords: str,
    similarity_type: str,
    tool_context: ToolContext,
) -> list[dict[str, Any]]:
    """
    This tool returns in general most similar caselaws provided the keywords. Agent also needs to provide
    if the similarity b/w keywords and cases are on the basis of 'Rules', 'Facts', 'Issues', 'Analysis'
    or 'Conclusion'. This is what the variable similarity_type is for, it should be exactly the same
    string as above values.

    Arg:
        keywords (str): A descriptive search sentence capturing the legal essence of the query.
            Example: "Court's power to appoint arbitrator when parties fail to agree under Arbitration Act"
            This gets embedded and matched semantically against case law FIRAC components.
        similarity_type (str): Which FIRAC component to search against. MUST be exactly one of:
            ['Rules', 'Facts', 'Issues', 'Analysis', 'Conclusion'].
            Choose based on query intent — do NOT always default to 'Facts'.

    Returns:
        list[dict[str, Any]]: List of relevant cases with their analysis, conclusion, court, and
            section references, in order of relevance.
    """

    valid_similarity_types = ["Rules", "Facts", "Issues", "Analysis", "Conclusion"]
    if similarity_type not in valid_similarity_types:
        logger.warning(f"Invalid similarity_type '{similarity_type}' received. Must be one of {valid_similarity_types}. Defaulting to 'Facts'.")
        similarity_type = "Facts"

    logger.debug(f"Caselaw Keywords: {keywords}")
    logger.debug(f"Similarity Type: {similarity_type}")

    embedder = OpenLargeAIEmbedder()
    weaviate_database = get_weaviate_db()

    embed_query = await embedder.embed_text(keywords)
    top_k = 10

    neo4j_client = get_neo4j_client(
        uri=neo4j_config.legal_neo4j_uri,
        user=neo4j_config.legal_neo4j_username,
        password=neo4j_config.legal_neo4j_password,
    )

    top_cases_relevant_to_keywords = await weaviate_database.search_similar_content_in_specific_cases(
        case_ids=None,
        query_embedding=embed_query,
        similarity_type=similarity_type,
    )

    weaviate_cases = {}
    keys = ["iLOCaseNo", "content", "court"]

    for o in top_cases_relevant_to_keywords.objects:
        case_dict: dict[str, Any] = {"type": similarity_type}
        current_case_id = o.properties.get("iLOCaseNo")
        weaviate_cases[current_case_id] = {key: o.properties[key] for key in keys}

    case_ids = [key for key in weaviate_cases]

    # Get analysis for each case
    cases_connected_to_sections = await neo4j_client.run_query(
        query=cypher_query_retrieve_cases_analysis_from_ids,
        parameters={
            "case_ids": case_ids,
            "BenchValue": None,
            "Court": None,
        },
        timeout=120
    )
    logger.debug("Completed neo4j call")

    for case in cases_connected_to_sections:
        current_case_id = case["ILOCaseNo"]
        case_dict = dict(case)

        case_dict = {
            key: value for key, value in case_dict.items() if key != "ILOCaseNo"
        }

        weaviate_cases[current_case_id].update(case_dict)

    output = [case for case in weaviate_cases.values()]

    # Write results directly to state for downstream agents (composer)
    existing = tool_context.state.get("caselaw_keyword_data", [])
    existing.extend(output)
    tool_context.state["caselaw_keyword_data"] = existing
    logger.debug(f"Wrote {len(output)} cases to state['caselaw_keyword_data']")

    return output
