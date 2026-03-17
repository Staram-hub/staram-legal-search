"""
This module contains Cypher queries used to interact with the Neo4j database.
"""

# ==================== Caselaw Retrieval Queries ========

cypher_query_get_caselaw_schema = """
CALL db.schema.visualization()
"""

# ============= Act -[*]-> Node Retrieval Queries ==============

cypher_query_get_node_attached_to_act = """
MATCH (a:Act)-[*1..8]->(n)
WHERE toLower(a.title) IN {act_list}
  AND any(label IN {labels_list} WHERE label IN labels(n))
RETURN a.title AS act_name, a.publish_date as act_publish_date, a.year as year,
       COLLECT({section_name: n.content, section_id: n.section_id, section_number: n.tag_id}) AS sections
"""

# ============= Legislation Retrieval Queries ==============

cypher_query_get_all_laws = """
MATCH (n:Law) WHERE NOT n.law_id CONTAINS '.' RETURN n
"""

cypher_query_get_acts_wrt_law = """
MATCH (act)-[:UNDER]->(n:Law {name: $law_name})
RETURN act.title AS act_title
"""

cypher_query_get_sections = """
MATCH p=(n:Act)-[*1..10]->(m:Section)
WHERE toLower(n.title) IN $act_names
  AND m.content IS NOT NULL
  AND NONE(x IN nodes(p)[1..-1] WHERE x:Act OR x:Rule)
RETURN n.title AS act_name, n.publish_date as act_publish_date, n.year as year,
       COLLECT({section_title: m.title, section_id: m.section_id, section_number: m.tag_id}) AS sections
"""

cypher_query_get_subsections = """
MATCH (s:Section)
WHERE s.section_id IN $sectionIds
OPTIONAL MATCH path=(s)-[*1..4]->(child)
WHERE child:SubSection OR child:Paragraph

WITH s, child,
     CASE
       WHEN child:SubSection THEN 'SubSection'
       WHEN child:Paragraph THEN 'Paragraph'
     END AS childType
WITH s, COLLECT(DISTINCT {
  childType: childType,
  childContent: child.content,
  childTagId: COALESCE(child.tag_id, "")
}) AS children
RETURN
  s.section_num AS section_number,
  s.content AS section_content,
  children
ORDER BY s.section_num
"""

# ============================== Rule Retrieval Queries ==============================

cypher_query_get_rules = """
match (a:Act)<--(r:Rule)
return r.title as rule_title, a.title as act_name, a.publish_date as act_publish_date, a.year as year
"""

cypher_query_get_all_rules_wrt_act = """
MATCH (a:Act)<-[]-(r:Rule)
WHERE toLower(toString(a.title)) IN $act_names
RETURN a.title AS act_name,a.publish_date as act_publish_date, a.year as year,
       COLLECT(r.title) AS rule_titles
"""

cypher_query_get_sections_related_to_rules = """
match (r:Rule)-->(s:Section)
where toLower(toString(r.title)) in $rule_titles
RETURN r.title AS rule_title,
   COLLECT({
     section_content: s.content,
     section_id: s.section_id
   }) AS sections
"""
# ============================== Notifications Retrieval Queries ==============================

cypher_query_get_notifications = """
MATCH (a:Act)<--(n:Notification)
WHERE toLower(toString(a.title)) IN $act_names
RETURN a.title AS act_name,a.publish_date as act_publish_date, a.year as year,
   COLLECT(n.section) AS notification_sections
"""

# ============================== V2 Retrieval Queries ==============================

cypher_query_get_nodes_v2 = """
MATCH p=(a:Act)-[*1..5]->(b)
WHERE toLower(toString(a.title)) IN $act_titles
  AND any(label IN labels(b) WHERE label IN $labels_list)
  AND NONE(x IN nodes(p)[1..-1] WHERE x:Act OR x:Rule)
WITH a, b
WITH a, collect(DISTINCT b) AS distinct_b_nodes
RETURN a.title AS act_title,
   [b IN distinct_b_nodes | {
     node_title: CASE
                   WHEN b.title IS NULL OR b.title = ""
                   THEN b.content
                   ELSE b.title
                 END,
     label: labels(b),
     node_id: CASE
        WHEN 'Section' IN labels(b)
        THEN b.section_id
        ELSE elementID(b)
        END
   }] AS connected_nodes
"""

cypher_query_v2_get_complete_node_info = """
MATCH p = (b)<-[*1..6]-(a:Act)
WHERE toLower(elementId(b)) IN $node_ids
   OR toLower(b.section_id) IN $node_ids
WITH b, min(length(p)) AS minLength
MATCH r=(b)<-[*1..6]-(firstAct:Act)
WHERE length(r) = minLength
WITH firstAct, collect(b) AS distinct_b_nodes
RETURN firstAct.title AS act_title,
   [b IN distinct_b_nodes | {
     node_content: CASE
                   WHEN b.content IS NULL OR b.content = ""
                   THEN b.title
                   ELSE b.content
                 END,
     label: labels(b),
     section_number_if_applicable: b.section_num,
     node_id: CASE 
        WHEN 'Section' IN labels(b) 
        THEN b.section_id 
        ELSE elementID(b) 
        END
   }] AS connected_nodes
"""

cypher_query_retrieve_cases_connected_to_sections = """
MATCH (c:Case)-[:REFERS_TO_SECTION]->(s:Section)
WHERE s.section_id IN $section_ids
    AND ($Court IS NULL OR toLower(c.Court) IN $Court)
    AND ($BenchValue IS NULL OR c.BenchValue >= $BenchValue)
RETURN
    c.ILOCaseNo AS case_id,
    c.display_name AS case_title,
    c.FIRAC_Conclusion AS case_conclusion,
    c.FIRAC_Analysis AS case_analysis,
    c.Court AS court_case,
    c.BenchValue AS case_bench_size,
    collect({
        sectionNumber: s.section_num,
        sectionTitle: s.title
    }) AS refers_to_sections
"""


cypher_query_retrieve_cases_from_ids = """
match (c:Case)
where ($Court IS NULL OR toLower(c.Court) IN $Court)
    AND ($BenchValue IS NULL OR c.BenchValue >= $BenchValue)
RETURN
    c.ILOCaseNo AS case_id,
    c.display_name AS case_title,
    c.FIRAC_Conclusion AS case_conclusion,
    c.FIRAC_Analysis AS case_analysis,
    c.Court AS court_case,
    c.BenchValue AS case_bench_size
"""

cypher_query_retrieve_cases_analysis_from_ids = """
match (c:Case)
where ($Court IS NULL OR toLower(c.Court) IN $Court)
    AND ($BenchValue IS NULL OR c.BenchValue >= $BenchValue)
    AND c.ILOCaseNo IN $case_ids
RETURN
    c.ILOCaseNo AS ILOCaseNo,
    c.display_name AS case_title,
    c.FIRAC_Conclusion AS case_conclusion,
    c.FIRAC_Analysis AS case_analysis,
    c.FIRAC_HeadNote as overall_case_summary,
    c.Court AS court_case,
    c.BenchValue AS case_bench_size
"""

cypher_query_fulltext_search_acts = """
WITH $query AS query
CALL db.index.fulltext.queryNodes("actTitleIndex", query)
YIELD node, score
RETURN DISTINCT node.title AS act_name, score AS search_score, node.publish_date as act_publish_date
ORDER BY score DESC
LIMIT $limit
"""

cypher_query_fulltext_search_rules = """
WITH $query AS query
CALL db.index.fulltext.queryNodes("ruleTitleIndex", query)
YIELD node, score
RETURN DISTINCT node.title AS rule_name, score AS search_score
ORDER BY score DESC
LIMIT $limit
"""
