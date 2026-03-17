
"""
This module contains predefined prompts for formatting outputs in various styles.
"""

from pydantic import BaseModel, Field
from typing import Literal


class ClassifyingLegalQuery(BaseModel):
    query_type: Literal["1", "2", "3", "4"] = Field(
        str,
        description="""
        String value representing the type of legal query, from "1" to "4"
        "1": Query Involving Only a Question of Interpretation of the Law.
        "2": Query Involving a judgment or Set of Judgments Around a Specific Issue.
        "3": Query Type: Synthesis of Facts and Law (Application to Scenario).
        "4": Query Type: Statutory + Case Law Synthesis.
        """,
    )


output_format_only_legal = """
Note: Please Adhere to below format strictly. Skipping any sections mentioned below would lead to Termination.

### Output Format

1.  Summary Answer (1–3 sentences)
    State the core legal principle or likely outcome concisely.
    If the law is unsettled, say so and indicate why (e.g., split of authority, factual dependency).
    Mention the statutory basis or key doctrine in brief.

2. Statutory / Legal Framework
    Quote or summarize the relevant statutory provisions, rules, or constitutional articles.
    Mention key definitions where applicable.
    If the law derives from case law rather than statute, state the doctrinal source clearly.

3. Case Laws
    List 2–5 important cases with:
    Citation, Court, Year
    Legal proposition / holding (1–2 lines)
    Do not cite any overruled precedents.

4. Detailed Legal Analysis
Provide the reasoning lawyers need - from principle to application structure this section:
    Rule: State the general rule derived from statute and case law.
    Interpretation / Explanation: Discuss how courts have interpreted the rule, including nuances.
    Application: Explain how the rule would operate in common or given scenarios.
    Exceptions / Limitations: Identify any exceptions, carve-outs, or contrary

5. Contrary Views / Adverse Authorities (optional if any)
    Mention minority opinions, contrary judgments, or unresolved splits.
    Briefly explain how they differ and whether they are persuasive or binding.

6. Conclusion (1–2 sentences)
    Restate the main principle and any key caveats.
    Highlight what determines the outcome (e.g., consent, contract language, statutory exceptions) [Don’t think we need it since the summary is at the top

7. References / Citations
Purpose: Give the lawyer source trails to verify and quote.
    Statutes, sections, and full case citations.
    Secondary sources (commentaries, treatises) if relevant.
"""

output_format_only_judgement_issue = """
Note: Please Adhere to below format strictly. Skipping any sections mentioned below would lead to Termination.

### Output Format

1. Summary Answer (1–3 sentences)
    State the consensus position or emerging trend in judicial interpretation.
    Note any conflicting judgments or jurisdictional splits.
    Identify the leading or binding authority, if clear.

2. Factual and Legal Context
    Briefly state the underlying issue(s) addressed in the key cases (e.g., type of dispute, procedural setting).
    Identify relevant statutory background (if any).
    Clarify the jurisdiction(s) covered

3. Key Judgments and Holdings
List 3–6 important cases, each with:
    Case name, citation, court, year.
    ratio decidendi (1–2 lines).
    Brief factual setting (if essential to understanding).
    Treatment by later courts (e.g., followed, distinguished).
Note – Do not cite overruled cases.

4. Comparative Judicial Reasoning
    Discuss points of convergence: principles consistently upheld.
    Discuss points of divergence: differing interpretations or fact-based distinctions.
    Explain which view is binding (based on court hierarchy).

5. Synthesized Legal Principle
    Extract the controlling test or standard that emerges across cases.
    Specify its scope, limits, and any conditions for its application.

6. Conclusion (1–2 sentences)
    Restate the dominant judicial position and its binding strength.
    Note any open questions or unsettled areas.

7. References / Citations
    Full case citations with reporter references.
    Cross-references to relevant statutory provisions, if cited by courts.
"""

output_format_synthesis_law_and_casefacts = """
Note: Please Adhere to below format strictly. Skipping any sections mentioned below would lead to Termination.

### Output Format

1. Summary Answer (1–3 sentences)
    State the probable legal result or liability outcome based on facts.
    Qualify the opinion if facts are incomplete or if multiple interpretations exist.
    Provide overall risk assessment (e.g., “likely valid,” “questionable,” “defensible”).

2. Material Facts
    Present only legally relevant facts
    Highlight timeline, conduct, parties’ roles, and any key documents/acts.
    Note any assumptions made where information is missing.

3. Applicable Law
    State the relevant statutory provisions and leading judicial principles.
    Identify the elements or tests that govern liability, validity, or compliance.
    Cite controlling authority or precedent.

4. Application of Law to Facts
    Discuss how courts have interpreted the rule, including nuances.
    Explain how the rule would operate in given scenario.

5. Discussion / Balancing Analysis
    Address counterarguments or weaknesses in the position.
    Compare with similar cases (analogize or distinguish).
    Identify any exceptions, carve-outs, or contrary.

6. Legal Assessment
    State your reasoned conclusion
    Suggest practical steps (e.g., remedial action, documentation, compliance fix).

7. Conclusion (1–2 sentences)
    Restate the outcome clearly and neutrally.
    Identify the key determinant (fact, document, or rule element).

8. References / Citations
    Case citations, sections, and authorities applied.
    Optionally: short note on each case’s relevance to facts.
"""

output_format_statutory_caselaw = """
Note: Please Adhere to below format strictly. Skipping any sections mentioned below would lead to Termination.

### Output Format

1. Summary Answer (1–3 sentences)
    State the integrated rule emerging from both statute and precedent.
    Mention whether the law is settled or evolving.
    Identify key statutory provision(s) and leading judgment(s).

2. Statutory Framework
    Quote or summarize the relevant sections, rules, or clauses.
    Highlight definitions and interpretive aids (explanations, exceptions, provisos).
    Mention legislative intent or amendments, if relevant.

3. Leading Case Law
List 2–5 principal cases, each with:
    Citation, Court, Year.
    Statutory provision considered.
    Key holding and rationale (1–2 lines).
    Note if it expanded, restricted, or clarified the statute

4. Synthesis of Statute and Judicial Interpretation
    Explain how courts have interpreted the statute — literal, purposive, or contextual.
    Identify areas of conflict (where courts have read beyond or limited text).
    Summarize the current operative interpretation.

5. Application / Practical Implications
    Explain how the integrated rule applies in typical or presented scenarios.
    Discuss any jurisdictional variations or pending appeals.
    Highlight compliance or drafting implications (for contracts, policies, etc.).

6. Exceptions
    Mention interpretive uncertainty, conflicting dicta, or amendments in pipeline.
    Note any minority or dissenting judicial positions.

7. Conclusion (1–2 sentences)
    Restate the current legal position succinctly.
    Add a caveat if the area remains unsettled or context-sensitive.

8. References / Citations
    Statutes with section numbers.
    Full case citations with pinpoint references.
    Optionally: law commission reports, explanatory notes, or commentary references.
"""


output_format_dict = {
    "1": output_format_only_legal,
    "2": output_format_statutory_caselaw,
    "3": output_format_synthesis_law_and_casefacts,
    "4": output_format_only_judgement_issue
}

output_type_dict = {
    "1": "Type 1: Query Involving Only a Question of Interpretation of the Law",
    "2": "Type 2: Query Involving a judgment or Set of Judgments Around a Specific Issue ",
    "3": "Type 3: Query Type: Synthesis of Facts and Law (Application to Scenario)",
    "4": "Type 4: Query Type: Statutory + Case Law Synthesis "
}

legal_head_standard_output = "Standard Legal Output"
