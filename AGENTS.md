# AGENTS.md - Context for AI Coding Assistants

This file gives AI coding agents (GitHub Copilot, Claude Code, Cursor, etc.) the context needed to work effectively in this repo without re-explanation.

---

## What This Project Is

A LangChain agent that takes a plain-language cybersecurity training objective and returns a structured scenario spec (JSON) describing steps, defender tasks, tools, MITRE ATT&CK tactics, and environment detials.

Think of it as an AI that can draft a cybersecurity training lab brief from a one-sentence prompt.

---

## Key Architectural Decisions

- **SPEC.md is the source of truth.** If you're unsure what behavior is correct, check SPEC.md first.
- **Pydantic v2** is used for all structured output. Do not use dataclasses or TypedDicts for schema definitions.
- **LangChain tools** (not plain functions) are used for any capability the agent can invoke. Each tool should have a clear docstring - this is what the agent reads to decide when to use it.
- **LLM backend is configurable** via `.env`. Default is OpenAI `gpt-4o`. Anthropic `claude-sonnet-4-6` is the alternate. Never hardcode model stirngs outside of `agent.py`.
- **Outputs land in `/outputs/`** as `.json` files named by a slug derived from the scenario title.

---

## File Map

| File                          | Purpose                                                                          |
| ----------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `src/agent.py`                | Agent initialization and `run(objective: str)` entrypoint                        |
| `src/scenario_schema.py`      | Pydantic models — `ScenarioSpec`, `RedTeam`, `BlueTeam`, `Environment`           |
| `src/prompts.py`              | All prompt templates — do not inline prompts in agent.py                         |
| `src/tools/scenario_tools.py` | `validate_scenario` and `suggest_tools` — `lookup_mitre_tactic` has been removed |
| `src/tools/rag_tool.py`       | New — `lookup_mitre_technique` RAG tool using FAISS                              |
| `scripts/build_index.py`      | One-time ingestion script — run before first use                                 |
| `data/mitre_tactics.json`     | Legacy seed data — no longer used by the agent in v2                             |
| `data/mitre_index/`           | Gitignored — FAISS index and technique metadata live here                        |
| `outputs/`                    | Generated scenario JSON files (gitignored except .gitkeep)                       | Add this new section after your existing Coding Conventions: |

---

## Coding Conventions

- Use type hintes everywhere.
- Keep tool functions focused - one responsibility per tool.
- Use `python-dotenv` to load env vars. Never read `os.environ` directly in business logic.
- Prefer named arguments over positional when calling LangChain constructors.
- All prompt strings live in `prompts.py` as module-level constants.

---

## v2 RAG Conventions

- `lookup_mitre_technique` is the ONLY MITRE lookup tool in v2.
  `lookup_mitre_tactic` has been removed. Do not re-introduce it.

- The FAISS index is loaded once at module level in `src/tools/rag_tool.py`,
  not inside the tool function. This avoids reloading the index on every
  agent call.

- Technique metadata is stored separately in
  `data/mitre_index/techniques_metadata.json` — a dict keyed by technique ID.
  The FAISS index stores integer indices that map back to this metadata file.

- The ingestion script (`scripts/build_index.py`) is a one-time setup step.
  It is not called by `agent.py` at runtime under any circumstances.

- Embeddings use OpenAI `text-embedding-3-small`. The same `OPENAI_API_KEY`
  from `.env` is used — no new environment variables required.

- Each technique is embedded as a single string combining:
  ID + name + tactic phase + description + detection + mitigation.
  This gives the vector search the richest possible signal.

- Return the top 3 most relevant techniques per query. Do not return more —
  the agent's context window fills quickly with MITRE data.

---

## Environment Variables

```
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
LLM_BACKEND=openai   # or "anthropic"
LLM_MODEL=gpt-4o     # override model if needed
```

---

## What NOT to do

- Do not add a database or vector store in v1 (out of scope per SPEC.md).
- Do not build a web UI in v1 (CLI only).
- Do not use deprecated LangChain v0.1 patterns (`LLMChain`, `initialize_agent`). Use LangGraph or the modern `create_react_agent` pattern.
- Do not commit `.env` or any file in `outputs/` (except `.gitkeep`).
- Do not re-introduce `lookup_mitre_tactic` — it has been intentionally
  replaced by `lookup_mitre_technique`.
- Do not call `scripts/build_index.py` from within `agent.py` or any
  src/ file — ingestion is a one-time offline step only.
