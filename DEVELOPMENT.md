# How It Was Made

## Code Generation Method

During the creation of this project a combination of spec-driven development and iterative prompting were used. A SPEC.md file and AGENTS.md file were used as the sources of truth to drive a spec-driven development workflow, combined with iterative prompting to drive a coding agent through the implementation one artifact at a time with human review at each step.

### Load Context Prompt:

"I'm building a LangChain cybersecurity scenario generation agent. Here is my AGENTS.md and SPEC.md - treat these as the source of truth for everything you generate. Do not deviate from the architecture, naming conventions, or stack decisions defined in these files."

- Model Used: Claude Sonnet 4-6

### Generation Prompts in order of use:

#### Prompt 1 -

"Using the input/output contracts in SPEC.md, generate `src/scenario_schema.py`.
This file should contain Pydantic v2 models only - no agent logic, no imports from LangChain. Models needed: `ScenarioSpec`, `RedTeam`, `BlueTeam`, and `Environment`. Every field should have a `Field(description=...)` so the LLM understands what to populate. The `difficulty` field should be a `Literal` type with exactly three values as defined in the spec."

- Model Used: Claude Sonnet 4-6

#### Prompt 2.1 -

"Generate `src/prompts.py`. This file should contain two module-level string constants only: `SYSTEM_PROMPT` and `SCENARIO_GENERATION_PROMPT`. The system prompt should establish the agent as a cybersecurity training scenario designer with knowledge of MITRE ATT&CK. The generation prompt should accept an `{objective}` placeholder. No functions, no imports, no logic - just the two string constants."

- Model Used: Claude Sonnet 4-6

#### Prompt 2.2 -

"Ensure that the system prompt in `src/prompts.py` instructs the agent to use its tools (lookup, validate) before returning."

- Model Used: Claude Sonnet 4-6

#### Prompt 3 -

"Generate `data/mitre_tactics.json` - a JSON object where each key is a MITRE ATT&CK tactic ID (e.g. `TA0001`) and each value is an object with `name` and `description` fields. Include all 14 enterprise tactics from TA0001 through TA 0043. This is seed data only - no code."

- Model Used: Claude Sonnet 4

#### Prompt 4.1 -

"Generate `src/tools/scenario_tools.py`. Using LangChain's `@tool` decorator, create three tools: `lookup_mitre_tactic(keyword: str)` which searches `data/mitre_tactics.json` for matching tactics, `validate_scenario(scenario_json: str)` which parses a JSON string and validates it against the `ScenarioSpec` Pydantic model, and `suggest_tools(role: str, tactic_or_technique: str)` which returns a list of relevant red or blue team security tools. Each tool must have a clear docstring - this is what the agent reads to decide when to call it. Import `ScenarioSpec` from `src/scenario_schema.py`."

- Model Used: Claude Sonnet 4

#### Prompt 4.2 -

"Ensure that in src/tools/scenario_tools.py validate_scenario handles both json.JSONDecodeError and Pydantic validation errors separately. Additionally ensure that these errors do not hault a process and that a retry can be attempted."

- Model Used: Claude Sonnet 4

#### Prompt 4.3 -

"Note for future developement that validate_scenario returns a JSON string with a status field, not a plain 'Valid' string. Tests should parse the return value and check result['status'] == 'valid'."

- Model Used: Claude Sonnet 4

#### Prompt 5 -

"Generate `src/agent.py`. Use the context from AGENTS.md and SPEC.md. Load environment variables with python-dotenv. Build the LLM in a `_build_llm()` function that reads `LLM_BACKEND` and `LLM_MODEL` from the environment and supports both `ChatOpenAI` (default) and `ChatAnthropic`. Create a ReAct agent using `create_react_agent` from LangGraph with the three tools from `src/tools/scenario_tools.py`. Expose a `run(objective: str) -> ScenarioSpec` function as the main entrypoint. The agent should use `SYSTEM_PROMPT` and `SCENARIO_GENERATION_PROMPT` imported from `src/prompts.py` - no inline prompt strings in this file. Parse the final agent response into a validated `ScenarioSpec` - strip markdown fences before parsing. Save the output to `/outputs/` as a JSON file named from a slug of the scenario title. Support running as a CLI script via `python -m src.agent` with the objective passed as a command line argument, with a default objective if none is provided."

- Model Used: Claude Sonnet 4

#### Prompt 6 -

"Generate `tests/test_agent.py` using pytest. No LLM calls — all tests should run without any API key.
Write tests for:

`ScenarioSpec` validates successfully with a complete valid object
`ScenarioSpec` raises a validation error when `difficulty` is not one of the three valid literals
`ScenarioSpec` raises a validation error when a required field like `blue_team` is missing
`lookup_mitre_tactic` returns a result containing 'TA0008' when called with 'lateral movement'
`lookup_mitre_tactic` returns all tactics (fallback behavior) when called with a nonsense keyword
`validate_scenario` returns a JSON string where `status == 'valid'` for a correct scenario JSON string
`validate_scenario` returns a JSON string where `status == 'error'` or contains an error key for malformed JSON
`suggest_tools` returns a JSON list containing 'Mimikatz' when called with role='red' and tactic='credential access'
`suggest_tools` returns a JSON list containing 'Splunk' when called with role='blue' and tactic='ransomware'

Important: `validate_scenario` returns a JSON string with a `status` field - parse the return value with `json.loads()` before asserting.
"

- Model Used: Claude Sonnet 4

#### Prompt 7 -

"Add verbose logging to the `run()` function in `src/agent.py` so we can see each agent step as it happens. Print a message when the agent starts, and print each tool call name and result as the agent invokes them. Use `print()` statements for simplicity."

- Model Used: Claude Sonnet 4-6
