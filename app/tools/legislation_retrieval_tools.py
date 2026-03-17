"""
This module provides tools for legal context processing
"""

from google.adk.tools import ToolContext
from app.services.neo4j_connection_pool import get_neo4j_client
from app.config import neo4j_config
from app.data.graph_data import meta_schema_info

from app.prompts.cypher_queries import (
    cypher_query_get_sections,
    cypher_query_get_subsections,
    cypher_query_get_node_attached_to_act,
    cypher_query_get_nodes_v2,
    cypher_query_v2_get_complete_node_info,
    cypher_query_get_all_laws,
    cypher_query_get_acts_wrt_law,
    cypher_query_get_acts_wrt_law,
    cypher_query_fulltext_search_acts,
)

from app.utils.get_logger import get_logger
import logging
import asyncio

logger = get_logger(name=__name__, level=logging.DEBUG)


async def get_all_laws() -> list[dict[str, str]]:
    """
    Get all the laws from the database.

    Returns:
        list[dict[str,str]]: A list containing dictionaries where keys are law names.
    """
    try:
        logger.debug("running get_all_laws")
        logger.debug(f"Executing query: {cypher_query_get_all_laws}")

        neo4j_client = get_neo4j_client(
            uri=neo4j_config.legal_neo4j_uri,
            user=neo4j_config.legal_neo4j_username,
            password=neo4j_config.legal_neo4j_password,
        )

        records = await neo4j_client.run_query(
            query=cypher_query_get_all_laws,
            timeout=120
        )
        processed_results = [dict(record) for record in records]

        logger.debug("Finished get_all_laws")
        logger.debug(len(processed_results))
        return processed_results

    except Exception as e:
        logger.error(f"Error in get_all_laws: {e}")
        return [{"result": "There seems to be an error in retrieving all laws."}]


async def get_acts_according_to_law_selected(law_name: str
) -> list[dict[str, str]]:
    """
    Get all acts related to a selected law.

    Args:
        law_name (str): The name of the law to retrieve acts for.

    Returns:
        list[dict[str,str]]: A list containing dictionaries where keys are act titles.
    """
    try:
        logger.debug("running get_acts_according_to_law_selected")
        logger.debug(f"Executing query: {cypher_query_get_acts_wrt_law} with law name: {law_name}")

        neo4j_client = get_neo4j_client(
            uri=neo4j_config.legal_neo4j_uri,
            user=neo4j_config.legal_neo4j_username,
            password=neo4j_config.legal_neo4j_password,
        )

        records = await neo4j_client.run_query(
            query=cypher_query_get_acts_wrt_law,
            parameters={"law_name": law_name},
            timeout=120
        )
        processed_results = [dict(record) for record in records]

        logger.debug("Finished get_acts_according_to_law_selected")
        logger.debug(len(processed_results))
        return processed_results

    except Exception as e:
        logger.error(f"Error in get_acts_according_to_law_selected: {e}")
        return [{"result": f"Error retrieving acts for law: {law_name}."}]


async def get_all_nodes_wrt_act(
    act_list: list[str], node_label_list: list[str]
) -> list[dict[str, str]]:
    """
    Get all nodes of label provided in node label list, for each the provided acts, input act strings
    should match exactly to Acts present in the database. To get the list of acts, use the `get_all_act`
    tool. To get all types of node labels connected to act, use 'get_legislation_nodes' tool to underetsand
    each node type present in the graph for retrieval.

    Retrieval will be using (a:Act)-[*1...10]->(n) where n in node_label_list and a.title in act_list to
    retrieve all connected nodes (Simple cypher query provided for explanation, more robust query is
    used for retrieval)

    Args:
        act_list (list[str]): List of acts to get sections for
        node_label_list (list[str]): List of labels of nodes to get nodes for, retrieves all nodes of
            given label type

    Returns:
        list[dict[str, str]]: Returns entire list of Acts, and along with them retrieves nodes (with
            some brief description) pertaining to that act.
    """

    logger.debug("Running get_all_nodes_wrt_act tool")
    node_label_list = node_label_list[: max(len(node_label_list), 2)]

    if len(act_list) <= 0:
        raise ValueError(f"Length of act_list found is {len(act_list)}")

    act_list = [act.lower().strip() for act in act_list if act.strip()]


    neo4j_client = get_neo4j_client(
        uri=neo4j_config.legal_neo4j_uri,
        user=neo4j_config.legal_neo4j_username,
        password=neo4j_config.legal_neo4j_password,
    )

    query_to_execute = cypher_query_get_node_attached_to_act.format(
            act_list=act_list,
            labels_list=node_label_list,
        )
    logger.debug(f"Executing query: {query_to_execute}")
    result = await neo4j_client.run_query(
        query=query_to_execute,
        timeout=120
    )
    logger.debug("Completed get_all_sections_per_act query")
    logger.debug("Finished get_all_nodes_wrt_act tool")

    return result


async def get_all_sections_per_act(act_list: list[str]) -> list[dict[str, str]]:
    """
    Get all section related to the provided acts, input strings should match exactly to Acts present
    in the database. To get the list of acts, use the `get_all_acts` tool.

    Args:
        act_list (list[str]): List of acts to get sections for

    Returns:
        list[dict[str, str]]: Returns entire list of Acts, and along with them retrieves sections (with
            some brief description) pertaining to that act.
    """
    logger.debug("Running get_all_sections_per_act")

    if len(act_list) <= 0:
        raise ValueError(f"Length of act_list found is {len(act_list)}")

    act_list = [act.lower().strip() for act in act_list if act.strip()]


    neo4j_client = get_neo4j_client(
        uri=neo4j_config.legal_neo4j_uri,
        user=neo4j_config.legal_neo4j_username,
        password=neo4j_config.legal_neo4j_password,
    )

    logger.debug(f"Executing query: {cypher_query_get_sections}")
    result = await neo4j_client.run_query(
        query=cypher_query_get_sections,
        parameters={"act_names": act_list},
        timeout=120
    )
    logger.debug("Finished get_all_sections_per_act")

    return result


async def get_all_subsections_or_paragraphs_per_section(section_id_list: list[str], tool_context: ToolContext):
    """
    For a given Section id retrieve all the subsections or paragraphs related to that section.

    Args:
        section_id_list (list[str]): List of section ids to get subsections or paragraphs for

    Returns:
        dict[str, dict[str, Any]]: Returns a dictionary where keys are section ids and values are dictionaries
            with further
    """
    logger.debug("Running get_all_subsections_or_paragraphs_per_section")

    if len(section_id_list) <= 0:
        raise ValueError(f"Length of section_id_list found is {len(section_id_list)}")


    neo4j_client = get_neo4j_client(
        uri=neo4j_config.legal_neo4j_uri,
        user=neo4j_config.legal_neo4j_username,
        password=neo4j_config.legal_neo4j_password,
    )

    logger.debug(f"Executing query: {cypher_query_get_subsections} with parameters: {{\"sectionIds\": {section_id_list}}}")
    result = await neo4j_client.run_query(
        query=cypher_query_get_subsections,
        parameters={"sectionIds": section_id_list},
        timeout=120
    )
    logger.debug("Completed get_all_subsections_or_paragraphs_per_section query")
    logger.debug("Finished get_all_subsections_or_paragraphs_per_section")

    # Write results directly to state for downstream agents (composer)
    existing = tool_context.state.get("legislation_subsections_data", [])
    existing.extend(result)
    tool_context.state["legislation_subsections_data"] = existing
    logger.debug(f"Wrote {len(result)} subsections to state['legislation_subsections_data']")

    return result


# -------------------------- V2 Version Tools ---------------------


async def get_legislation_nodes() -> dict[str, dict[str, str]]:
    """
    This tool provides metadata information about the node types that are present in the
    legislation graph itself. Helps understand what labels of nodes are present in the
    graph itself and what is their purpose and description

    Returns:
        list[dict[str,str]]: Meta data information about the legislation knowledge graph
    """
    logger.debug("Running get_legislation_nodes")
    result = meta_schema_info
    logger.debug("Finished get_legislation_nodes")
    return result


async def get_all_nodes_wrt_label_per_act(
    labels_list: list[str], act_list: list[str]
) -> list[dict[str, str]]:
    """
    Provided a list of labels and acts, retrieve all nodes of that label connected to the act. To get
    list of relevant labels use `get_legislation_nodes` to retrieve all labels of relevant nodes present
    in the legislation knowledge graph. To get all acts present in the knowledge graph, use `get_all_acts`

    Args:
        labels_list (list[str]): List of all relevant labels nodes you want to retrieve connected to
            an act.
        act_list (list[str]): List of acts to get sections for

    Returns:
        list[dict[str, str]]: Returns entire list of Acts, and along with them retrieves nodes with provided
            labels (with some brief description) pertaining to that act.
    """
    logger.debug("Running get_all_nodes_wrt_label_per_act")
    logger.debug(f"acts list - {act_list}")
    if len(act_list) <= 0:
        raise ValueError(f"Length of act_list found is {len(act_list)}")
    if len(labels_list) <= 0:
        raise ValueError(f"Length of act_list found is {len(labels_list)}")

    act_list = [act.lower().strip() for act in act_list if act.strip()]


    neo4j_client = get_neo4j_client(
        uri=neo4j_config.legal_neo4j_uri,
        user=neo4j_config.legal_neo4j_username,
        password=neo4j_config.legal_neo4j_password,
    )

    logger.debug(f"Executing query: {cypher_query_get_nodes_v2} with parameters: {{\"act_titles\": {act_list}, \"labels_list\": {labels_list}}}")
    result = await neo4j_client.run_query(
        query=cypher_query_get_nodes_v2,
        parameters={"act_titles": act_list, "labels_list": labels_list},
        timeout=120
    )
    logger.debug("Completed get_all_nodes_wrt_label_per_act tool")
    logger.debug("Finished get_all_nodes_wrt_label_per_act")

    return result


async def get_all_nodes_using_nodeid(node_ids: list[str], tool_context: ToolContext) -> list[dict[str, str]]:
    """
    This tool retrieves nodes based on their unique node IDs. This is useful when you have specific
    node IDs and want to fetch detailed information about those nodes from the legislation knowledge
    graph.

    Args:
        node_ids (list[str]): List of unique node IDs to retrieve information for.

    Returns:
        list[dict[str, str]]: Returns a list of nodes with their details based on provided node ids,
            along with their connected act
    """
    logger.debug("Running get_all_nodes_using_nodeid")
    logger.info(f"Node ids for get_all_nodes_using_nodeid: {node_ids}")
    if len(node_ids) <= 0:
        raise ValueError(f"Length of node_ids found is {len(node_ids)}")

    node_ids = [node_id.lower().strip() for node_id in node_ids if node_id.strip()]

    neo4j_client = get_neo4j_client(
        uri=neo4j_config.legal_neo4j_uri,
        user=neo4j_config.legal_neo4j_username,
        password=neo4j_config.legal_neo4j_password,
    )

    logger.debug(f"Executing query: {cypher_query_v2_get_complete_node_info} with parameters: {{\"node_ids\": {node_ids}}}")
    result = await neo4j_client.run_query(
        query=cypher_query_v2_get_complete_node_info,
        parameters={"node_ids": node_ids},
        timeout=120
    )
    logger.debug("Completed get_all_nodes_using_nodeid tool")
    logger.debug("Finished get_all_nodes_using_nodeid")

    # Write results directly to state for downstream agents (composer)
    existing = tool_context.state.get("legislation_nodes_data", [])
    existing.extend(result)
    tool_context.state["legislation_nodes_data"] = existing
    logger.debug(f"Wrote {len(result)} nodes to state['legislation_nodes_data']")

    return result

async def get_top_acts_by_keywords(keywords: list[str]) -> list[dict[str, str]]:
    """
    Retrieves the top 50 acts for each provided keyword using full-text search.
    Queries are run in parallel using asyncio.gather.

    Args:
        keywords (list[str]): A list of keywords to search for.

    Returns:
        list[dict[str, str]]: A list of dictionaries, where each dictionary represents an act
                              and contains its name, search score, publish date, and year.
    """
    # start_time = time.time()
    all_results = []
    try:
        logger.debug("Running get_top_acts_by_keywords tool")
        if not keywords:
            raise ValueError("Keywords list cannot be empty.")

        neo4j_client = get_neo4j_client(
            uri=neo4j_config.legal_neo4j_uri,
            user=neo4j_config.legal_neo4j_username,
            password=neo4j_config.legal_neo4j_password,
        )

        async def fetch_acts_for_keyword(keyword: str):
            query_params = {"query": f"{keyword} OR {keyword}*", "limit": 50}
            logger.debug(f"Executing query for keyword '{keyword}': {cypher_query_fulltext_search_acts}")
            records = await neo4j_client.run_query(
                query=cypher_query_fulltext_search_acts,
                parameters=query_params,
                timeout=120
            )
            return [dict(record) for record in records]

        tasks = [fetch_acts_for_keyword(keyword) for keyword in keywords]
        results_per_keyword = await asyncio.gather(*tasks)

        for result_list in results_per_keyword:
            all_results.extend(result_list)

        logger.debug(f"Finished get_top_acts_by_keywords, total acts retrieved: {len(all_results)}")
        return all_results

    except Exception as e:
        logger.error(f"Error in get_top_acts_by_keywords: {e}")
        return [{"result": f"There was an error retrieving acts for keywords: {e}"}]
