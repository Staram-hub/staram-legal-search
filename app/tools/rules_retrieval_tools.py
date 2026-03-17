from google.adk.tools import ToolContext
from app.services.neo4j_connection_pool import get_neo4j_client
from app.config import neo4j_config
from app.prompts.cypher_queries import (
    cypher_query_get_all_rules_wrt_act,
    cypher_query_get_rules,
    cypher_query_get_sections_related_to_rules,
    cypher_query_fulltext_search_rules,
)

from app.utils.get_logger import get_logger
import logging

logger = get_logger(name=__name__, level=logging.DEBUG)


async def get_all_rules() -> list[dict[str, str]]:
    """
    Get all the rules, associated Parent act wrt to that rule and some description for them

    Returns:
        list[dict[str, str]]: A list containing dictionary where keys are rule names and values are their
            descriptions along with the parent act.
    """

    logger.debug("running get_all_rules")


    neo4j_client = get_neo4j_client(
        uri=neo4j_config.legal_neo4j_uri,
        user=neo4j_config.legal_neo4j_username,
        password=neo4j_config.legal_neo4j_password,
    )

    result = await neo4j_client.run_query(
        query=cypher_query_get_rules,
        timeout=120
        )

    return result


async def get_rules_wrt_act(act_list: list[str], tool_context: ToolContext) -> list[dict[str, str]]:
    """
    Get all rules related to the provided acts, input strings should match exactly to Acts present
    in the database. To get the list of acts, use the `get_all_acts` tool.

    Args:
        act_list (list[str]): List of acts to get rules for

    Returns:
        list[dict[str, str]]: Returns entire list of Acts, and along with them retrieves rules (with
            some brief description) related to that act.
    """
    logger.debug("Running get_rules_wrt_act tool")

    if len(act_list) <= 0:
        raise ValueError(f"Length of act_list found is {len(act_list)}")

    act_list = [act.lower().strip() for act in act_list if act.strip()]
    logger.debug(f"This tools is running with the act list: {act_list}")

    neo4j_client = get_neo4j_client(
        uri=neo4j_config.legal_neo4j_uri,
        user=neo4j_config.legal_neo4j_username,
        password=neo4j_config.legal_neo4j_password,
    )

    result = await neo4j_client.run_query(
        query=cypher_query_get_all_rules_wrt_act,
        parameters={"act_names": act_list},
        timeout=120
    )
    logger.debug("Completed Running get_rules_wrt_act tool")

    # Write results directly to state for downstream agents (composer)
    existing = tool_context.state.get("rules_data", [])
    existing.extend(result)
    tool_context.state["rules_data"] = existing
    logger.debug(f"Wrote {len(result)} rules to state['rules_data']")

    return result


async def get_all_sections_per_rule(rule_list: list[str], tool_context: ToolContext) -> list[dict[str, str]]:
    """
    Get all section related to the provided rules, input strings should match exactly to rule name present
    in the database. To get the list of rules, use the `get_rules_wrt_act` tool.

    Args:
        rule_list (list[str]): List of rules to get sections for

    Returns:
        list[dict[str, str]]: Returns entire list of rules, and along with them retrieves sections (with
            some brief description) pertaining to each rule.
    """
    logger.debug("Running get_all_sections_per_rule")

    if len(rule_list) <= 0:
        raise ValueError(f"Length of rule_list found is {len(rule_list)}")

    rule_list = [rule.lower().strip() for rule in rule_list if rule.strip()]
    logger.warning(f"Rules query: {rule_list}")

    neo4j_client = get_neo4j_client(
        uri=neo4j_config.legal_neo4j_uri,
        user=neo4j_config.legal_neo4j_username,
        password=neo4j_config.legal_neo4j_password,
    )

    result = await neo4j_client.run_query(
        query=cypher_query_get_sections_related_to_rules,
        parameters={"rule_titles": rule_list},
        timeout=120
    )
    logger.debug("Completed get_all_sections_per_rule query")

    # Write results directly to state for downstream agents (composer)
    existing = tool_context.state.get("rule_sections_data", [])
    existing.extend(result)
    tool_context.state["rule_sections_data"] = existing
    logger.debug(f"Wrote {len(result)} rule sections to state['rule_sections_data']")

    return result


async def get_top_rules_by_keywords(keywords: list[str], limit: int = 10) -> list[dict[str, str]]:
    """
    Search for rules using keywords via full-text search on rule titles.
    Extract 3-5 highly relevant keywords from the user query that capture the essence 
    of the legal domain or specific rules. Avoid vague keywords like "rule", "law", "act".
    
    Args:
        keywords (list[str]): List of 3-5 relevant keywords to search for in rule titles
        limit (int): Maximum number of rules to return (default: 10)
    
    Returns:
        list[dict[str, str]]: List of matching rules with their titles and relevance scores
    """
    # start_time = time.time()
    try:
        logger.debug(f"Running get_top_rules_by_keywords with keywords: {keywords}")
        
        if not keywords or len(keywords) == 0:
            raise ValueError("keywords list cannot be empty")
        
        # Join keywords with OR for full-text search
        query_string = " OR ".join([f"{kw.strip()}" for kw in keywords if kw.strip()])

        neo4j_client = get_neo4j_client(
            uri=neo4j_config.legal_neo4j_uri,
            user=neo4j_config.legal_neo4j_username,
            password=neo4j_config.legal_neo4j_password,
        )
        
        result = await neo4j_client.run_query(
            query=cypher_query_fulltext_search_rules,
            parameters={"query": query_string, "limit": limit},
            timeout=120
        )
        
        logger.debug(f"Found {len(result)} rules matching keywords")
        return result
        
    except Exception as e:
        logger.error(f"Error in get_top_rules_by_keywords: {e}")
        return [{"result": f"Error retrieving rules by keywords: {str(e)}"}]