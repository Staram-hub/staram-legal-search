meta_schema_info: dict[str, dict[str, str]] = {
    "Act": {
        "description": "Represents a primary legislative document, such as a statute or law passed\
        by a legislative body. It contains core identifying information like its title, year of enactmen\
        , preamble, and the governing body.",
        "purpose": "Serves as the central anchor for a piece of legislation. Its purpose is to group\
        all its constituent parts (Chapters, Sections) and to link to related information like court\
        cases that reference it, rules derived from it, and detailed conceptual analyses (e.g., Key\
        Dates, Regulatory Bodies).",
    },
    "Chapter": {
        "description": "A structural node representing a major division within an Act, typically containing\
        a collection of related Sections.",
        "purpose": "To organize the content of a lengthy Act into thematic or logical blocks, making\
        the legal text easier to navigate and reference.",
    },
    "Part": {
        "description": "A high-level structural division within an Act, which can contain multiple\
        Chapters or Sections.",
        "purpose": "To provide the broadest level of structural organization within a legal documen\
        , often used in very large and complex Acts.",
    },
    "Section": {
        "description": "Represents a specific, numbered section of a legal document like an Act or\
        Rule. It is a key unit of legal text containing a specific provision or regulation.",
        "purpose": "To provide a granular, citable unit of law. It is the primary node for linking\
        legal text to specific court case references (via the 'REFERENCES' relationship) and for anchoring\
        detailed semantic analysis (via the 'DEFINED_BY' relationship from metadata nodes).",
    },
    "SubSection": {
        "description": "A subdivision of a Section, representing a more specific clause or provision\
        within that section's text.",
        "purpose": "To break down the text of a Section into smaller, more manageable logical units\
        for finer-grained analysis and referencing.",
    },
    "Paragraph": {
        "description": "A paragraph-level chunk of text, often a subdivision of a Section or SubSection.",
        "purpose": "To provide a highly granular level of text segmentation, allowing for precise linking\
        and analysis of individual sentences or clauses within the legal document.",
    },
    "Concept": {
        "description": "Represents an abstract legal idea, action, entity, or theme (e.g., 'obligation\
        ', 'penalty', 'jurisdiction'). It is not a specific piece of text but a normalized term.",
        "purpose": "To act as a semantic bridge or a conceptual tag. Its purpose is to normalize and\
        link specific, structured information from various metadata nodes to a shared vocabulary. This\
        enables powerful semantic queries across different Acts and legal contexts (e.g., 'Find all\
        provisions that IMPOSE an obligation on a director').",
    },
    "Applicability_of_Statute": {
        "description": "A metadata node that captures structured information about the scope and jurisdiction\
        of an Act, including the parties it applies to.",
        "purpose": "To explicitly define and query the scope of a law. This allows users to easily\
        determine who or what an Act governs without having to read and interpret the entire text.",
    },
    "Key_Dates": {
        "description": "A metadata node that extracts and stores important dates related to an Act,\
        such as its enactment date, effective date, or amendment dates, along with the nature of the event.",
        "purpose": "To provide a quick, structured timeline of an Act's lifecycle. This is useful for\
        understanding when different versions of the law were in effect.",
    },
    "Definitions_and_Terms": {
        "description": "A metadata node that explicitly captures a term and its corresponding definition\
        as provided within the text of an Act.",
        "purpose": "To create a queryable glossary of all terms defined within a legal document, making\
        it easy to look up official definitions and understand the specific meaning of terms in that\
        legal context.",
    },
    "Procedural_Steps": {
        "description": "A metadata node that outlines a sequence of actions or procedures mandated\
        by an Act, including the entities involved and the order of operations.",
        "purpose": "To model legal and administrative processes in a structured way. This allows users\
        to understand and analyze workflows defined by law, such as application processes or compliance steps.",
    },
    "Regulatory_Bodies": {
        "description": "A metadata node representing an authority, committee, or organization that\
        is established, empowered, or mentioned within an Act, detailing its name, role, and jurisdiction.",
        "purpose": "To explicitly identify and model the government and regulatory bodies involved\
        in an Act's framework. This makes it easy to query which bodies are created by which laws and\
        what their functions are.",
    },
    "Eligibility_Criteria": {
        "description": "A metadata node that structures the criteria that must be met for a person,\
        entity, or situation to qualify for a certain status, right, or program under an Act.",
        "purpose": "To make qualification requirements easily queryable. This helps users quickly determine\
        if they meet the necessary conditions for a specific legal provision.",
    },
    "Judicial_Precedents": {
        "description": "A metadata node that summarizes a key legal principle established by a court\
        case that interprets or affects an Act.",
        "purpose": "To link statutory law (the Act) with case law. This node helps users understand\
        how courts have interpreted the Act, which is essential for a complete legal analysis.",
    },
    "Amendments_and_Repeals": {
        "description": "A metadata node that records changes made to an Act, such as which sections\
        have been amended or repealed, by which amending act, and on what date.",
        "purpose": "To track the evolution of a law over time. This is critical for determining which\
        version of a law was in force at a specific point in time and understanding how the law has changed.",
    },
    "Sublaw": {
        "description": "Represents a secondary legal instrument, such as a rule, regulation, or orde\
        , that is derived from or sits under a primary Law or Act.",
        "purpose": "To model the relationship between primary legislation (Act, Law) and the subordinate\
        legislation that implements or details it. It allows for tracing legal authority from a hig\
        -level law down to its specific implementing rules.",
    },
}

court_names = [
    "DELHI HIGH COURT",
    "BOMBAY HIGH COURT",
    "CALCUTTA HIGH COURT",
    "SUPREME COURT OF INDIA",
    "MADRAS HIGH COURT",
    "KARNATAKA HIGH COURT",
    "GUJARAT HIGH COURT",
    "HIMACHAL PRADESH HIGH COURT",
    "ANDHRA PRADESH HIGH COURT",
    "UTTARAKHAND HIGH COURT",
    "RAJASTHAN HIGH COURT",
    "KERALA HIGH COURT",
    "MADHYA PRADESH HIGH COURT",
    "PUNJAB AND HARYANA HIGH COURT",
    "ALLAHABAD HIGH COURT",
    "ORISSA HIGH COURT",
    "JHARKHAND HIGH COURT",
    "JAMMU AND KASHMIR HIGH COURT",
    "PATNA HIGH COURT",
    "GAUHATI HIGH COURT",
    "STATE CONSUMER DISPUTES REDRESSAL COMMISSION",
]
