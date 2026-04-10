from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# LangChain / LangGraph imports
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from src.prompts import SYSTEM_PROMPT, SCENARIO_GENERATION_PROMPT
from src.scenario_schema import ScenarioSpec
from src.tools.scenario_tools import lookup_mitre_tactic, validate_scenario, suggest_tools


load_dotenv()

PROJECT_ROOT = Path(__file__).parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _build_llm():
    """Build an LLM instance based on environment configuration.

    Reads LLM_BACKEND and LLM_MODEL from the environment. Supports OpenAI
    (ChatOpenAI) and Anthropic (ChatAnthropic). This implementation does NOT
    use any hardcoded model strings — both backend and model must be set via
    environment variables. An EnvironmentError is raised if either is missing
    or if an unsupported backend is specified.
    """
    import os

    backend = os.getenv("LLM_BACKEND")
    model = os.getenv("LLM_MODEL")

    if not backend:
        raise EnvironmentError(
            "LLM_BACKEND environment variable is not set. Set it to 'openai' or 'anthropic'."
        )
    if not model:
        raise EnvironmentError(
            "LLM_MODEL environment variable is not set. No hardcoded defaults are used."
        )

    backend_lower = backend.lower()
    if backend_lower == "anthropic":
        return ChatAnthropic(model=model)
    if backend_lower == "openai":
        return ChatOpenAI(model=model)

    raise EnvironmentError(
        f"Unsupported LLM_BACKEND '{backend}'. Use 'openai' or 'anthropic'."
    )


def _strip_markdown_fences(text: str) -> str:
    """Remove surrounding Markdown code fences and trim whitespace."""
    # Remove ```json ... ``` or ``` ... ``` fences
    fenced = re.sub(r"^```[\w+\-]*\n|\n```$", "", text.strip())
    return fenced


def _slugify(title: str) -> str:
    """Create a filesystem-safe slug from a title."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "scenario"


def run(objective: str) -> ScenarioSpec:
    """Main entrypoint: run the ReAct agent to generate a ScenarioSpec.

    The function constructs prompts from src.prompts, runs the agent with
    the configured LLM and tools, parses and validates the returned JSON,
    saves the scenario to outputs/{slug}.json, and returns the validated
    ScenarioSpec instance.
    """
    llm = _build_llm()

    print(f"\n[agent] Starting scenario generation...")
    print(f"[agent] Objective: {objective}")
    print(f"[agent] LLM backend: {llm.__class__.__name__}\n")

    # create agent with tools
    agent = create_agent(
        model=llm,
        tools=[lookup_mitre_tactic, suggest_tools, validate_scenario],
    )

    prompt = SCENARIO_GENERATION_PROMPT.format(objective=objective)
    # Pass system prompt as first message, followed by the human objective
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    # run the agent to produce a response
    response = agent.invoke({"messages": messages})

    # Log each intermediate step (tool calls and their results)
    for msg in response["messages"]:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"[tool call] {tc['name']}  args={tc['args']}")
        elif isinstance(msg, ToolMessage):
            # Truncate long results to keep the console readable
            preview = msg.content[:300].replace("\n", " ")
            ellipsis = "..." if len(msg.content) > 300 else ""
            print(f"[tool result] ({msg.name})  {preview}{ellipsis}")

    raw_response = response["messages"][-1].content
    print(f"\n[agent] Generation complete. Parsing response...")

    # strip markdown fences if present
    cleaned = _strip_markdown_fences(raw_response)

    # Attempt to extract JSON object from the response
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find the first JSON object in the text
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if not m:
            raise ValueError("Agent response did not contain valid JSON.")
        parsed = json.loads(m.group(0))

    # Validate against Pydantic model
    scenario = ScenarioSpec.model_validate(parsed)

    # Save to outputs
    slug = _slugify(scenario.title)
    out_path = OUTPUT_DIR / f"{slug}.json"
    out_path.write_text(scenario.model_dump_json(indent=2))

    return scenario


if __name__ == "__main__":
    default_objective = (
        "Teach a blue team analyst to detect and respond to a ransomware attack targeting a Windows environment."
    )
    objective = sys.argv[1] if len(sys.argv) > 1 else default_objective
    result = run(objective)
    print(result.model_dump_json(indent=2))
