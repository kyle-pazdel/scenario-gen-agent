# AGENTS.md - Context for AI Coding Assistants

This file gives AI coding agents (GitHub Copilot, Claude Code, Cursor, etc.) the context needed to work effectively in this repo without re-explanation.

---

## What This Project Is

A LangChain agent that takes a plain-language cybersecurity training objective and returns a structured scenario spec (JSON) describing steps, defender tasks, tools, MITRE ATT&CK tactics, and environment detials.

THink of it as an AI that can draft a cybersecurity training lab brief from a one-sentence prompt.

---

## Key Architectural Decisions

- **SPEC.md is the source of truth.** If you're unsure what behavior is correct, check SPEC.md first.
- **Pydantic v2** is used for all structured output. Do not use dataclasses or TypedDicts for schema definitions.
- **LangChain tools** (not plain functions) are used for any capability the agent can invoke. Each tool should have a clear docstring - this is what the agent reads to decide when to use it.
- **LLM backend is configurable** via `.env`. Default is OpenAI `gpt-4o`. Anthropic `claude-sonnet-4-6` is the alternate. Never hardcode model stirngs outside of `agent.py`.
- **Outputs land in `/outputs/`** as `.json` files named by a slug derived from the scenario title.

---

## File Map

| File                          | Purpose                                                                |
| ----------------------------- | ---------------------------------------------------------------------- |
| `src/agent.py`                | Agent initialization and `run(objective: str)` entrypoint              |
| `src/scenario_schema.py`      | Pydantic models - `ScenarioSpec`, `RedTeam`, `BlueTeam`, `Environment` |
| `src/prompts.py`              | All prompt templates - do not inline prompts in agent.py               |
| `src/tools/scenario_tools.py` | LangChain `@tool` functions the agent can call                         |
| `data/mitre_tactics.json`     | Seed data: MITRE ATT&CK tactic IDs and descriptions                    |
| `outputs/`                    | Generated scenario JSON files (gitignored except .gitkeep)             |

---

## Coding Conventions

- Use type hintes everywhere.
- Keep tool functions focused - one responsibility per tool.
- Use `python-dotenv` to load env vars. Never read `os.environ` directly in business logic.
- Prefer named arguments over positional when calling LangChain constructors.
- All prompt strings live in `prompts.py` as module-level constants.

---

## Environment Variables

---

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
