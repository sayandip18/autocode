# AI Research Agent Architecture & Roadmap

This document outlines the cognitive design, state management, tool specifications, and evolution strategy for the AI Research Assistant backend.

## 1. Agent Overview & Persona

- **Objective**: Execute autonomous, deep-dive research across web sources and GitHub repositories to synthesize highly contextual technical answers.
- **Core Paradigm**: Evolving from a simple synchronous Tool-Calling loop into a cyclic, stateful graph using **LangGraph**.

---

## 2. Current Architecture (Phase 1)

Currently, the system operates as a single-loop **ReAct (Reasoning + Acting)** agent utilizing OpenAI's native tool-calling capabilities exposed via FastAPI endpoints.

- **LLM**: `gpt-4o` (or preferred model)
- **Execution Flow**:
  User Query ➔ LLM decides tool invocation ➔ Results appended to context ➔ LLM synthesizes final response.

---
