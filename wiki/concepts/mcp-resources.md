---
title: MCP Resources
type: concept
status: draft
sources: ["03-mcp-tools-resources-prompts-420d2910"]
tags: [mcp, resources]
---

# MCP Resources

MCP Resources expose contextual data — such as files, databases, or APIs — without necessarily performing actions. They support read-only or read-dominant access patterns.

Per [[03-mcp-tools-resources-prompts-420d2910]], resources differ from tools and prompts by their passive, data-oriented role in the protocol.

Resources are still governed by the [[Agent Tool Interface]] because the host decides how context is described, retrieved, and validated. They also sit on the [[Context Boundary]]: exposing a file, database row, or API result can change what the model knows even when no direct side effect occurs.

## Related

- [[Model Context Protocol]]
- [[Agent Tool Interface]]
- [[Context Boundary]]
- [[Agent Interoperability]]
