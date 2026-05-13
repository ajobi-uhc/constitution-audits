"""Prompts for attribute extraction."""

# Attribution prompt for extracting 10 attributes from a single query
# Matches the original chunky-post-training-3 pipeline
SINGLE_ATTRIBUTION_PROMPT = '''A user wrote this query to a large language model assistant:

<query>

{{ query }}

</query>

Write a list of 10 attributes which describe this query, encompassing whichever aspects of content, style, formatting, tone, structure, perspective, et cetera which are most relevant. Write each as a sentence starting with "The query", listed in XML tags from <1> to <10>. Avoid referencing overly specific words in the query. You should only describe attributes present in the query, not those that are absent. Include nothing else in your response.'''

