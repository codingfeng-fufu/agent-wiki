---
title: Agent Development Knowledge Map
type: analysis
status: draft
sources:
  - "01-openai-agents-guardrails-87ce73bd"
  - "02-openai-agents-tracing-ea05beb6"
  - "03-mcp-tools-resources-prompts-420d2910"
  - "04-langgraph-durable-execution-2b964c83"
  - "05-google-adk-multi-agent-patterns-78ef6d88"
  - "06-autogen-agent-and-multi-agent-applications-8cb555fe"
  - "07-a2a-agent-interoperability-fc58e8a2"
  - "08-owasp-llm-agent-security-9253bc51"
tags: [agent-development, analysis, map]
---

# Agent Development Knowledge Map

This map connects the initial agent-development source cards into a working wiki structure.

## Source Cards

- [[01-openai-agents-guardrails-87ce73bd]] frames [[Agent Guardrails]], [[Input Guardrails]], [[Output Guardrails]], [[Tool Safety]], and [[Agent Evaluation]].
- [[02-openai-agents-tracing-ea05beb6]] frames [[Agent Tracing]], [[Agent Observability]], [[Tool Call Logs]], [[Agent Regression Testing]], and [[Replayable Agent Runs]].
- [[03-mcp-tools-resources-prompts-420d2910]] frames [[Model Context Protocol]], [[MCP Tools]], [[MCP Resources]], and [[MCP Prompts]].
- [[04-langgraph-durable-execution-2b964c83]] frames [[Durable Agent Execution]], [[Agent Checkpointing]], [[Human in the Loop]], [[Idempotent Tool Calls]], and [[Agent State Graph]].
- [[05-google-adk-multi-agent-patterns-78ef6d88]] frames [[Multi-Agent Systems]], [[Coordinator Agent]], [[Planner Executor Pattern]], [[Reviewer Agent]], and [[Fan Out Gather Pattern]].
- [[06-autogen-agent-and-multi-agent-applications-8cb555fe]] frames [[AutoGen]], [[Message Driven Agents]], [[Multi-Agent Orchestration]], and [[Agent Runtime]].
- [[07-a2a-agent-interoperability-fc58e8a2]] frames [[Agent2Agent Protocol]], [[Agent Interoperability]], [[Protocol Boundary]], and [[MCP vs A2A]].
- [[08-owasp-llm-agent-security-9253bc51]] frames [[Prompt Injection]], [[Agent Security]], [[Tool Abuse]], [[Sensitive Data Exposure]], and [[Least Privilege]].

## Cross-Cutting Threads

- Safety starts with [[Agent Guardrails]] and expands into [[Agent Security]], [[Least Privilege]], and [[Tool Safety]].
- Reliability combines [[Durable Agent Execution]], [[Agent Checkpointing]], [[Replayable Agent Runs]], and [[Agent Tracing]].
- Coordination spans [[Multi-Agent Systems]], [[Multi-Agent Orchestration]], [[Message Driven Agents]], and [[Agent Interoperability]].
- Protocol design separates [[Model Context Protocol]] for context/tool exposure from [[Agent2Agent Protocol]] for agent-to-agent coordination.

## Open Synthesis Questions

- Which `llmw` commands should eventually become [[MCP Tools]], and which wiki files should be exposed as [[MCP Resources]]?
- What guardrail and trace data should be captured before `llmw ingest run` writes pages?
- Should ingestion be split into reader, writer, linker, reviewer, and security-review roles?
