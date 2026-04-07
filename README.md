Load Context Prompt:
"I'm building a LangChain cybersecurity scenario generation agent. Here is my AGENTS.md and SPEC.md - treat these as the source of truth for everything you generate. Do not deviate from the architecture, naming conventions, or stack decisions defined in these files."

Generation Promts in order of use:

Prompt 1 -
"Using the input/output contracts in SPEC.md, generate `src/scenario_schema.py`.
This file should contain Pydantic v2 models only - no agent logic, no imports from LangChain. Models needed: `ScenarioSpec`, `RedTeam`, `BlueTeam`, and `Environment`. Every field should have a `Field(description=...)` so the LLM understands what to populate. The `difficulty` field should be a `Literal` type with exactly three values as defined in the spec."

Prompt 2 -
"Generate `src/prompts.py`. This file should contain two module-level string constants only: `SYSTEM_PROMPT` and `SCENARIO_GENERATION_PROMPT`. The system prompt should establish the agent as a cybersecurity training scenario designer with knowledge of MITRE ATT&CK. The generation prompt should accept an `{objective}` placeholder. No functions, no imports, no logic - just the two string constants."
