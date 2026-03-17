"""
Enhanced Legal Assistant with ADK ParallelAgent + SequentialAgent Pipeline
Architecture: Head Agent → SequentialAgent[Discovery → ParallelAgent[Legislation, Caselaw] → Composer]
"""

import json
import os
import re
import datetime

from google.genai.types import GenerateContentConfig
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps.app import App

from app.tools.classify_query import classify_query
from app.tools.legislation_retrieval_tools import (
    get_all_nodes_wrt_label_per_act,
    get_all_nodes_using_nodeid,
    get_all_subsections_or_paragraphs_per_section,
    get_top_acts_by_keywords,
)
from .tools.rules_retrieval_tools import (
    get_rules_wrt_act,
    get_all_sections_per_rule,
)
from .tools.caselaw_retrieval import (
    get_court_names,
    get_caselaw_per_section,
    get_caselaw_per_keyword_only,
)
from .config import config
from .prompts.agentic_prompts import (
    DISCOVERY_AGENT_INSTRUCTION,
    LEGISLATION_RESEARCH_INSTRUCTION_TEMPLATE,
    LEGISLATION_TASK_WITH_TOOLS,
    LEGISLATION_TASK_EMPTY,
    CASELAW_RESEARCHER_INSTRUCTION_TEMPLATE,
    CASELAW_SKIP_INSTRUCTION,
    CASELAW_PROCEED_INSTRUCTION,
    HEAD_AGENT_INSTRUCTION,
    LEGAL_REPORT_COMPOSER_INSTRUCTION,
)

config_args = {
    "temperature": 0.0
}


# ==================== HELPER: Parse JSON from LLM output ====================

def _parse_json_from_string(raw: str) -> dict | list | None:
    """Parse JSON from a string that may be wrapped in markdown code blocks."""
    if not raw or not isinstance(raw, str):
        return None
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = re.sub(r'^```json\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
        elif cleaned.startswith("```"):
            cleaned = re.sub(r'^```\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
        return json.loads(cleaned)
    except Exception as e:
        print(f"[PARSE ERROR] Failed to parse JSON: {e}")
        print(f"[PARSE ERROR] Raw (first 300 chars): {raw[:300]}")
        return None


# ==================== CALLABLE INSTRUCTION PROVIDERS ====================

def legislation_research_instruction(ctx) -> str:
    """Callable instruction for legislation_research_agent.
    Handles statutory content retrieval. Rules retrieval is decided by the agent itself
    after reading the statutory content — matching the old approach where the legislation
    agent had full context before deciding on rules.
    """
    node_ids = ctx.state.get("node_ids", [])
    section_ids = ctx.state.get("section_ids", [])
    act_list = ctx.state.get("act_list", [])

    if not node_ids and not section_ids:
        legislation_task_body = LEGISLATION_TASK_EMPTY
    else:
        legislation_task_body = LEGISLATION_TASK_WITH_TOOLS.format(
            node_ids=json.dumps(node_ids),
            section_ids=json.dumps(section_ids),
        )

    return LEGISLATION_RESEARCH_INSTRUCTION_TEMPLATE.format(
        node_ids=json.dumps(node_ids),
        section_ids=json.dumps(section_ids),
        act_list=json.dumps(act_list),
        legislation_task_body=legislation_task_body,
    )


def composer_instruction(ctx) -> str:
    """Callable instruction for legal_report_composer.
    Reads all research data from state (populated by tools via ToolContext and callbacks)
    and injects it directly into the prompt so the composer LLM can see the actual data.
    """
    query_type = ctx.state.get("query_type", "3")
    output_format = ctx.state.get("output_format", "")
    is_non_legal = ctx.state.get("is_non_legal_query", False)

    # Build research data section from state
    legislation_sources = ctx.state.get("legislation_sources", {})
    caselaw_sources = ctx.state.get("caselaw_sources", [])

    research_parts = []
    research_parts.append(f"**Query Type**: {query_type}")
    research_parts.append(f"**Output Format**: {output_format}")
    research_parts.append(f"**Is Non-Legal Query**: {is_non_legal}")

    if legislation_sources:
        research_parts.append("\n### Legislation Sources:")
        research_parts.append(json.dumps(legislation_sources, indent=2, default=str))
    else:
        research_parts.append("\n### Legislation Sources: None found")

    if caselaw_sources:
        research_parts.append("\n### Caselaw Sources:")
        research_parts.append(json.dumps(caselaw_sources, indent=2, default=str))
    else:
        research_parts.append("\n### Caselaw Sources: None found")

    research_data = "\n".join(research_parts)

    return LEGAL_REPORT_COMPOSER_INSTRUCTION.replace("{research_data}", research_data)


def caselaw_researcher_instruction(ctx) -> str:
    """Callable instruction for caselaw_researcher. Reads state from discovery phase."""
    section_ids = ctx.state.get("section_ids", [])
    query_type = ctx.state.get("query_type", "3")
    is_non_legal = ctx.state.get("is_non_legal_query", False)

    # Skip caselaw for non-legal queries
    if is_non_legal:
        skip_instruction = CASELAW_SKIP_INSTRUCTION
    # For Type 1, skip caselaw unless explicitly needed
    elif query_type == "1":
        skip_instruction = CASELAW_SKIP_INSTRUCTION
    else:
        skip_instruction = CASELAW_PROCEED_INSTRUCTION

    return CASELAW_RESEARCHER_INSTRUCTION_TEMPLATE.format(
        section_ids=json.dumps(section_ids),
        query_type=query_type,
        skip_instruction=skip_instruction,
    )


# ==================== CALLBACKS ====================

def discovery_callback(callback_context: CallbackContext) -> None:
    """
    After discovery agent completes, extract structured data from discovery_findings
    and populate state with act_list, node_ids, section_ids, initial_rules.
    """
    print("\n" + "=" * 80)
    print("[CALLBACK] discovery_callback triggered")
    print("=" * 80)

    findings = callback_context.state.get("discovery_findings")

    # Parse if string
    if isinstance(findings, str):
        findings = _parse_json_from_string(findings)

    if not findings or not isinstance(findings, dict):
        print("[CALLBACK] No valid discovery_findings found, setting empty state")
        callback_context.state["act_list"] = []
        callback_context.state["node_ids"] = []
        callback_context.state["section_ids"] = []
        return

    # Extract act_list
    acts = findings.get("acts", [])
    act_list = []
    for act in acts:
        if isinstance(act, dict) and act.get("act_title"):
            act_list.append(act["act_title"])
    callback_context.state["act_list"] = act_list
    print(f"[CALLBACK] Extracted act_list: {act_list}")

    # Extract node_ids and section_ids from selected_nodes
    all_node_ids = []
    section_ids = []
    selected_nodes = findings.get("selected_nodes", [])
    for node in selected_nodes:
        if isinstance(node, dict):
            node_id = node.get("node_id")
            if node_id:
                all_node_ids.append(node_id)
                if node.get("label") == "Section":
                    section_ids.append(node_id)

    callback_context.state["node_ids"] = all_node_ids
    callback_context.state["section_ids"] = section_ids
    print(f"[CALLBACK] Extracted node_ids ({len(all_node_ids)}): {all_node_ids}")
    print(f"[CALLBACK] Extracted section_ids ({len(section_ids)}): {section_ids}")

    print("=" * 80 + "\n")


def collect_legislation_sources_callback(callback_context: CallbackContext) -> None:
    """Collects legislation AND rules findings from tool-populated state into legislation_sources for the composer.
    Tools write directly to state via ToolContext, so we read from state keys instead of parsing agent JSON."""
    print("\n" + "=" * 80)
    print("[CALLBACK] collect_legislation_sources_callback triggered")
    print("=" * 80)

    legislation_sources = callback_context.state.get("legislation_sources", {})

    # Read tool-populated state (written by tools via ToolContext)
    nodes_data = callback_context.state.get("legislation_nodes_data", [])
    subsections_data = callback_context.state.get("legislation_subsections_data", [])
    rules_data = callback_context.state.get("rules_data", [])
    rule_sections_data = callback_context.state.get("rule_sections_data", [])

    print(f"[CALLBACK] Processing {len(nodes_data)} nodes, {len(subsections_data)} subsections from tool state")
    print(f"[CALLBACK] Processing {len(rules_data)} rules, {len(rule_sections_data)} rule sections from tool state")

    # Process legislation nodes (from get_all_nodes_using_nodeid)
    for node in nodes_data:
        if isinstance(node, dict):
            act_title = node.get("act_title") or node.get("actTitle")
            if act_title and act_title not in legislation_sources:
                legislation_sources[act_title] = {
                    "act_title": act_title,
                    "act_id": node.get("act_id"),
                    "year": node.get("year"),
                    "publish_date": node.get("act_publish_date"),
                    "sections": [],
                    "rules": [],
                    "nodes": [],
                }
            if act_title:
                node_info = {
                    "node_id": node.get("node_id") or node.get("nodeId"),
                    "node_label": node.get("node_label") or node.get("label"),
                    "title": node.get("title"),
                    "content": node.get("content"),
                }
                label = node_info.get("node_label", "")
                if label in ("Section", "Subsection"):
                    legislation_sources[act_title]["sections"].append(node_info)
                else:
                    legislation_sources[act_title]["nodes"].append(node_info)

    # Process subsections (from get_all_subsections_or_paragraphs_per_section)
    for subsection in subsections_data:
        if isinstance(subsection, dict):
            act_title = subsection.get("act_title") or subsection.get("actTitle")
            if act_title and act_title in legislation_sources:
                node_info = {
                    "node_id": subsection.get("node_id") or subsection.get("nodeId"),
                    "node_label": subsection.get("node_label") or subsection.get("label") or "Subsection",
                    "title": subsection.get("title"),
                    "content": subsection.get("content"),
                }
                legislation_sources[act_title]["sections"].append(node_info)

    # Process rules (from get_rules_wrt_act and get_all_sections_per_rule)
    for rule in rules_data:
        if isinstance(rule, dict):
            rule_title = rule.get("rule_title") or rule.get("ruleTitle")
            if rule_title and rule_title not in legislation_sources:
                legislation_sources[rule_title] = {
                    "act_title": rule_title,
                    "type": "rule",
                    "sections": [],
                    "rules": [],
                    "nodes": [],
                }
            if rule_title:
                legislation_sources[rule_title]["rules"].append(rule)
                print(f"[CALLBACK] Added rule: {rule_title}")

    for rule_section in rule_sections_data:
        if isinstance(rule_section, dict):
            rule_title = rule_section.get("rule_title") or rule_section.get("ruleTitle")
            if rule_title and rule_title in legislation_sources:
                legislation_sources[rule_title]["nodes"].append(rule_section)

    callback_context.state["legislation_sources"] = legislation_sources
    print(f"[CALLBACK] legislation_sources keys: {list(legislation_sources.keys())}")
    print("=" * 80 + "\n")


def collect_caselaw_sources_callback(callback_context: CallbackContext) -> None:
    """Collects caselaw findings from tool-populated state into caselaw_sources for the composer.
    Tools write directly to state via ToolContext, so we read from state keys instead of parsing agent JSON."""
    print("\n" + "=" * 80)
    print("[CALLBACK] collect_caselaw_sources_callback triggered")
    print("=" * 80)

    caselaw_sources = callback_context.state.get("caselaw_sources", [])
    seen_case_ids = {c.get("case_id") for c in caselaw_sources if c.get("case_id")}

    # Read tool-populated state (written by tools via ToolContext)
    caselaw_section_data = callback_context.state.get("caselaw_section_data", [])
    caselaw_keyword_data = callback_context.state.get("caselaw_keyword_data", [])

    all_cases = caselaw_section_data + caselaw_keyword_data
    print(f"[CALLBACK] Processing {len(caselaw_section_data)} section-based + {len(caselaw_keyword_data)} keyword-based cases from tool state")

    for case in all_cases:
        if isinstance(case, dict):
            case_id = case.get("iLOCaseNo") or case.get("case_id")
            if case_id and case_id not in seen_case_ids:
                case_info = {
                    "case_id": case_id,
                    "case_title": case.get("case_title") or case.get("iLOCaseNo"),
                    "case_conclusion": case.get("case_conclusion"),
                    "case_analysis": case.get("case_analysis"),
                    "court": case.get("court"),
                    "bench_size": case.get("bench_size") or case.get("BenchCoramValue"),
                    "refers_to_sections": case.get("refers_to_sections", []),
                    "content": case.get("content"),
                    "type": case.get("type"),
                }
                caselaw_sources.append(case_info)
                seen_case_ids.add(case_id)
                print(f"[CALLBACK] Added case: {case_id}")

    callback_context.state["caselaw_sources"] = caselaw_sources
    print(f"[CALLBACK] caselaw_sources count: {len(caselaw_sources)}")
    print("=" * 80 + "\n")


def format_legal_citations_callback(callback_context: CallbackContext) -> None:
    """Formats citations in the final legal opinion with inline citations and reference links."""
    final_opinion = callback_context.state.get("final_legal_opinion", "")
    legislation_sources = callback_context.state.get("legislation_sources", {})
    caselaw_sources = callback_context.state.get("caselaw_sources", [])

    if not final_opinion:
        return

    # Build citation lists
    legislation_citations = []
    caselaw_citations = []

    citation_num = 1
    for act_title, act_data in legislation_sources.items():
        citation = {
            "number": citation_num,
            "act_title": act_title,
            "year": act_data.get("year"),
            "sections": [],
        }
        for section in act_data.get("sections", []):
            section_ref = {
                "number": section.get("section_number"),
                "title": section.get("section_title"),
                "has_subsections": len(section.get("subsections", [])) > 0,
            }
            citation["sections"].append(section_ref)

        for rule in act_data.get("rules", []):
            citation["sections"].append({
                "type": "rule",
                "title": rule.get("rule_title"),
            })

        legislation_citations.append(citation)
        citation_num += 1

    for case in caselaw_sources:
        case_id = case.get("case_id", "")

        citation = {
            "number": citation_num,
            "case_id": case_id,
            "case_title": case.get("case_title"),
            "court": case.get("court"),
            "bench_size": case.get("bench_size"),
            "refers_to_sections": case.get("refers_to_sections", []),
        }
        caselaw_citations.append(citation)
        citation_num += 1

    # Build formatted references section
    references_text = "\n\n---\n\n## References\n\n"

    if legislation_citations:
        references_text += "### Legislation\n\n"
        for cit in legislation_citations:
            year_str = f", {cit['year']}" if cit["year"] else ""
            references_text += f"**[{cit['number']}]** {cit['act_title']}{year_str}\n"
            for section in cit["sections"]:
                if section.get("type") == "rule":
                    references_text += f"   - Rule: {section['title']}\n"
                else:
                    subsec_note = " (with subsections)" if section.get("has_subsections") else ""
                    references_text += f"   - Section {section['number']}: {section.get('title', '')}{subsec_note}\n"
            references_text += "\n"

    if caselaw_citations:
        references_text += "### Case Law\n\n"
        for cit in caselaw_citations:
            bench_str = f", {cit['bench_size']}-judge bench" if cit.get("bench_size") else ""
            references_text += f"**[{cit['number']}]** [{cit['case_title']}]\n"
            references_text += f"   - Court: {cit['court']}{bench_str}\n"
            references_text += f"   - Case ID: `{cit['case_id']}`\n"

            if cit["refers_to_sections"]:
                section_refs = [f"Section {s.get('sectionNumber', 'N/A')}" for s in cit["refers_to_sections"]]
                references_text += f"   - Refers to sections: {', '.join(section_refs)}\n"
            references_text += "\n"

    formatted_opinion = final_opinion
    if not formatted_opinion.endswith("\n"):
        formatted_opinion += "\n"
    formatted_opinion += references_text

    callback_context.state["formatted_legal_opinion"] = formatted_opinion


# ==================== PHASE 1: DISCOVERY AGENT ====================

legislation_discovery_agent = LlmAgent(
    model=config.worker_model,
    name="legislation_discovery_agent",
    description="Discovers relevant Acts, Rules, and structural nodes for a legal query. First phase of the research pipeline.",
    generate_content_config=GenerateContentConfig(**config_args),
    instruction=DISCOVERY_AGENT_INSTRUCTION,
    tools=[
        get_top_acts_by_keywords,
        get_all_nodes_wrt_label_per_act,
    ],
    output_key="discovery_findings",
    after_agent_callback=discovery_callback,
)


# ==================== PHASE 2A: LEGISLATION RESEARCH AGENT (Acts + Conditional Rules) ====================

legislation_research_agent = LlmAgent(
    model=config.worker_model,
    name="legislation_research_agent",
    description="Retrieves complete statutory content and conditionally retrieves rules if needed.",
    generate_content_config=GenerateContentConfig(**config_args),
    instruction=legislation_research_instruction,
    tools=[
        get_all_nodes_using_nodeid,
        get_all_subsections_or_paragraphs_per_section,
        get_rules_wrt_act,
        get_all_sections_per_rule,
    ],
    # output_key removed: tools write full data to state via ToolContext,
    # so no need for the agent to generate a large JSON output
    after_agent_callback=collect_legislation_sources_callback,
)


# ==================== PHASE 2C: CASELAW RESEARCHER ====================

caselaw_researcher = LlmAgent(
    model=config.worker_model,
    name="caselaw_researcher",
    description="Retrieves and analyzes relevant case law using hybrid Neo4j + Weaviate search.",
    generate_content_config=GenerateContentConfig(**config_args),
    instruction=caselaw_researcher_instruction,
    tools=[
        get_court_names,
        get_caselaw_per_section,
        get_caselaw_per_keyword_only,
    ],
    # output_key removed: tools write full data to state via ToolContext,
    # so no need for the agent to generate a large JSON output
    after_agent_callback=collect_caselaw_sources_callback,
)


# ==================== PHASE 2: PARALLEL DEEP RESEARCH ====================

parallel_deep_research = ParallelAgent(
    name="parallel_deep_research",
    description="Runs legislation research (with conditional rules) and caselaw retrieval in parallel.",
    sub_agents=[
        legislation_research_agent,
        caselaw_researcher,
    ],
)


# ==================== PHASE 3: FINAL COMPOSITION (mostly unchanged) ====================

legal_report_composer = LlmAgent(
    model=config.critic_model,
    name="legal_report_composer",
    description="Synthesizes research into final legal opinion following type-specific format",
    generate_content_config=GenerateContentConfig(**config_args),
    instruction=composer_instruction,
    output_key="final_legal_opinion",
    after_agent_callback=format_legal_citations_callback,
)


# ==================== RESEARCH PIPELINE: Sequential[Discovery → Parallel → Composer] ====================

legal_research_pipeline = SequentialAgent(
    name="legal_research_pipeline",
    description="Complete legal research pipeline: discovery → parallel deep research → composition",
    sub_agents=[
        legislation_discovery_agent,
        parallel_deep_research,
        legal_report_composer,
    ],
)


# ==================== LEGAL HEAD AGENT (Root Agent) ====================

legal_head_agent = LlmAgent(
    name="legal_head_agent",
    model=config.worker_model,
    description="Legal Head Agent - the primary orchestrator for Indian legal research queries.",
    generate_content_config=GenerateContentConfig(**config_args),
    instruction=HEAD_AGENT_INSTRUCTION.format(
        current_date=datetime.datetime.now().strftime("%Y-%m-%d"),
    ),
    tools=[
        classify_query,
    ],
    sub_agents=[
        legal_research_pipeline,
    ],
)


# ==================== APP SETUP ====================

root_agent = legal_head_agent
app = App(root_agent=root_agent, name="app")
