---
title: Index
type: index
---

# Index

Generated from `48` wiki pages.

## Source Pages

- [[01 openai agents guardrails]] `sources:1` - This source card points to the OpenAI Agents SDK guardrails documentation. It is useful for building a wiki section on agent safety boundaries, validation stages, and failure handl
- [[02 openai agents tracing]] `sources:1` - This source card points to the OpenAI Agents SDK tracing documentation. It is useful for a wiki section on how to debug, replay, and evaluate agent behavior.
- [[03 mcp tools resources prompts]] `sources:1` - This source card points to the MCP concepts documentation for [[MCP Tools]], [[MCP Resources]], and [[MCP Prompts]]. It is useful for comparing local CLI tools with protocol-native
- [[04 langgraph durable execution]] `sources:1` - This source card points to LangGraph documentation on durable execution, persistence, and human-in-the-loop workflows.
- [[05 google adk multi agent patterns]] `sources:1` - This source card points to the Google Agent Development Kit documentation on multi-agent systems.
- [[06 autogen agent and multi agent applications]] `sources:1` - This source card points to Microsoft AutoGen documentation on agents and multi-agent applications.
- [[07 a2a agent interoperability]] `sources:1` - This source card points to the Agent2Agent protocol documentation. It is useful for a wiki section on cross-agent interoperability and protocol boundaries.
- [[08 owasp llm agent security]] `sources:1` - This source card points to the OWASP Top 10 for LLM Applications. It is useful for a security-focused wiki section on [[Prompt Injection]], [[Sensitive Data Exposure]], [[Tool Abus

## Concept Pages

- [[Agent Checkpointing]] `sources:1` - Agent checkpointing is the practice of serializing and persisting agent state at defined points during execution to enable recovery, debugging, and auditing.
- [[Agent Evaluation]] `sources:2` - Agent evaluation checks whether agent behavior remains safe, useful, and reproducible. Per [[01-openai-agents-guardrails-87ce73bd]], guardrails provide validation signals for unsaf
- [[Agent Guardrails]] `sources:1` - Agent guardrails are validation boundaries around an agent workflow. The OpenAI Agents SDK guardrails source card frames them as mechanisms for constraining unsafe inputs, malforme
- [[Agent Interoperability]] `sources:1` - Agent interoperability is the ability of independently developed, deployed, or governed agents to collaborate meaningfully — exchanging tasks, state, or messages — while respecting
- [[Agent Observability]] `sources:1` - Agent observability is the ability to inspect, debug, and evaluate agent behavior beyond the final answer. The tracing source card frames traces as a structured record of agent beh
- [[Agent Regression Testing]] `sources:1` - Agent regression testing reruns representative tasks to detect behavior changes. The tracing source card connects traces to evaluation and regression testing.
- [[Agent Runtime]] `sources:4` - An agent runtime is the execution environment responsible for managing agent lifecycle, message routing, state persistence, tool invocation, and observability.
- [[Agent Security]] `sources:3` - Agent security is the design of controls for systems where model outputs can affect tools, files, network calls, or data disclosure. The OWASP source card frames prompt injection,
- [[Agent State Graph]] `sources:1` - An agent state graph is a formal representation of agent behavior as a directed graph where nodes represent states or actions and edges represent transitions governed by conditions
- [[Agent Tool Interface]] `sources:1` - An agent tool interface is the abstraction layer where a model, agent, or host interacts with external capabilities. It defines how capabilities are described, invoked, validated,
- [[Agent Tracing]] `sources:1` - Agent tracing records structured information about an agent run. The tracing source card identifies model calls, tool calls, handoffs, guardrails, and workflow steps as trace-worth
- [[Agent2Agent Protocol]] `sources:1` - The Agent2Agent (A2A) Protocol is a specification for enabling structured, secure, and discoverable communication between autonomous agents across runtime boundaries, organizations
- [[AutoGen]] `sources:1` - AutoGen is a Microsoft framework for building multi-agent applications using message-driven, role-based agents.
- [[Context Boundary]] `sources:2` - A context boundary is the trust and permission boundary between a model or host and the external context it can access. It determines what data is exposed, what actions are permitt
- [[Coordinator Agent]] `sources:1` - A coordinator agent is a role-based agent responsible for orchestrating interactions among other agents, typically by delegating subtasks, aggregating results, and enforcing execut
- [[Durable Agent Execution]] `sources:1` - Durable agent execution refers to the ability of an agent to survive interruptions, failures, or long durations by persisting state and supporting resumption from well-defined chec
- [[Fan Out Gather Pattern]] `sources:1` - A concurrency pattern in multi-agent systems where a coordinator agent distributes independent subtasks to multiple agents in parallel (fan out), then collects and synthesizes thei
- [[Human in the Loop]] `sources:1` - Human-in-the-loop (HITL) refers to agent workflows that intentionally pause execution to await human input, review, or approval before proceeding.
- [[Idempotent Tool Calls]] `sources:1` - Idempotent tool calls are operations that produce the same observable result when invoked multiple times with the same inputs — critical for safe retries in [[Durable Agent Executi
- [[Input Guardrails]] `sources:1` - Input guardrails validate or classify user input, source content, or workflow state before an agent proceeds. The guardrails source card distinguishes them from [[Output Guardrails
- [[Least Privilege]] `sources:1` - Least privilege means granting an agent or tool only the permissions needed for the current task. The OWASP source card lists it as a relevant security concept for agentic risk.
- [[MCP Prompts]] `sources:1` - MCP Prompts represent reusable interaction templates — structured instructions, examples, or system message fragments — that guide model behavior. They are composable and versionab
- [[MCP Resources]] `sources:1` - MCP Resources expose contextual data — such as files, databases, or APIs — without necessarily performing actions. They support read-only or read-dominant access patterns.
- [[MCP Tools]] `sources:1` - MCP Tools expose discrete, invocable actions that a model or host can execute. They are distinct from resources and prompts in that they produce side effects or compute results.
- [[MCP vs A2A]] `sources:1` - MCP (Model Context Protocol) and A2A (Agent2Agent Protocol) address complementary but non-overlapping interoperability concerns:
- [[Message Driven Agents]] `sources:1` - Message-driven agents interact primarily through asynchronous or synchronous message passing rather than direct function calls or shared memory.
- [[Model Context Protocol]] `sources:1` - The Model Context Protocol (MCP) is the standard interface for tools, resources, and prompts in this wiki: it defines how agents interact with external capabilities through three c
- [[Multi-Agent Orchestration]] `sources:1` - Multi-agent orchestration refers to the mechanisms and patterns used to coordinate behavior, data flow, and control among multiple autonomous agents.
- [[Multi-Agent Systems]] `sources:1` - Multi-agent systems (MAS) are architectures in which multiple autonomous agents interact to solve tasks that are beyond the capability of any single agent.
- [[Output Guardrails]] `sources:1` - Output guardrails validate an agent result before it is returned, stored, or passed to a tool. The guardrails source card highlights malformed outputs, policy violations, and unsaf
- [[Planner Executor Pattern]] `sources:1` - A multi-agent pattern where one agent (the planner) generates a sequence or structure of actions, and another (the executor) carries them out — often with feedback loops for refine
- [[Prompt Injection]] `sources:1` - Prompt injection is a core LLM application risk identified by the OWASP source card. In this wiki context, the immediate concern is raw source text that may contain instructions th
- [[Protocol Boundary]] `sources:2` - A protocol boundary is the interface layer where agents (or systems) enforce rules governing interaction — including authentication, authorization, message validation, capability n
- [[Replayable Agent Runs]] `sources:2` - Replayable agent runs preserve enough run context to inspect or reproduce behavior later. The tracing source card motivates debugging and replay, while the durable execution source
- [[Reviewer Agent]] `sources:1` - A reviewer agent is a specialized agent that critiques outputs, validates correctness, checks safety or coherence, and optionally triggers revision or escalation.
- [[Sensitive Data Exposure]] `sources:1` - Sensitive data exposure is a security risk for LLM and agent systems. The OWASP source card specifically calls out sensitive information disclosure in prompts, traces, and logs.
- [[Tool Abuse]] `sources:1` - Tool abuse occurs when model-controlled actions are misused or triggered unsafely. The OWASP source card highlights tool or plugin misuse when model output controls actions.
- [[Tool Call Logs]] `sources:1` - Tool call logs record tool invocations, results, and failures during an agent run. The tracing source card identifies tool calls as part of the structured record needed to debug ag
- [[Tool Safety]] `sources:2` - Tool safety is the design of constraints around actions that an agent can invoke. The guardrails source card connects guardrails to tool permissions, while the OWASP source card hi

## Analysis Pages

- [[Agent Development Knowledge Map]] `sources:8` - This map connects the initial agent-development source cards into a working wiki structure.
