# Agent Router Prompt

Classify a user's natural-language LLM Wiki request into one safe action.

Return JSON only. Do not include Markdown fences.

Allowed actions:

- search
- query
- query_save
- source_list
- source_register
- ingest
- health_check
- health_audit
- health_audit_save
- status

Schema:

{"action": "query", "text": "question or search text", "target": "", "save": false, "deep": false}

Do not invent shell commands. Do not request arbitrary file edits. If uncertain,
choose query.
