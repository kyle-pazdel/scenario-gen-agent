# Scenario Generation Agent - SPEC.md

> **This file is the source of truth for this project.**
> If the code and this spec disagree, fix the code.

---

## 1. What We're Building

A LangChain agent (Python) that accepts a high-level cybersecurity training objective and generates a fully structured scenario spec - including attacker steps, defender tasks, tools involved, and difficulty metadata.

This converts expert knowledge into deployable, structured training content at machine speed.

---

## 2. Primary Input / Output Contract

### Input

A plain-language training objective string.

**Example:**

```
"Teach a blue team analyst to detect and respond to a ransomware attack targetting a Windows environment."
```

\*\*\* Output
A structured JSON scenario object conforming to the `ScenarioSpec` Pydantic model (see `src/scenario_schema.py`).

**Example output shape:**

```json
{
  "title": "Ransomware Detection & Response",
  "difficulty": "intermediate",
  "mitre_tactics": ["TA0001", "TA0002", "TA0008", "TA0040"],
  "red_team": {
    "objective": "Encrypt critical files and exfiltrate data before detection",
    "mitre_tactics": ["TA0002", "TA0008", "TA0040"],
    "steps": [
      "Establish initial access via phishing email",
      "Move laterally using PsExec",
      "Deploy ransomware payload to shared drives"
    ],
    "tools": ["Mimikatz", "PsExec", "custom encryptor"]
  },
  "blue_team": {
    "objective": "Detect the intrusion and contain the ransomware before full encryption",
    "mitre_tactics": ["TA0001", "TA0002", "TA0008", "TA0040"],
    "steps": [
      "Monitor SIEM for anomalous login activity",
      "Isolate affected host from network",
      "Recover files from backup"
    ],
    "tools": ["Splunk", "Windows Event Logs", "Wireshark"]
  },
  "environment": {
    "os": "Windows Server 2019",
    "network_topology": "flat corporate LAN with AD",
    "services": ["Active Directory", "SMB file shares", "RDP"]
  },
  "learning_objectives": [
    "Identify lateral movement indicators in Windows event logs",
    "Understand ransomware kill chain",
    "Practice incident containment procedures"
  ],
  "estimated_duration_minutes": 60
}
```

---

## 3. Agent Architecture

```
User Input (objective string)
        │
        ▼
  ┌─────────────┐
  │  LangChain  │  ← Uses OpenAI or Anthropic LLM
  │    Agent    │
  └──────┬──────┘
         │ calls
    ┌────┴─────────────────────┐
    │         Tools            │
    │  - lookup_mitre_tactic   │  ← looks up MITRE ATT&CK tactic by keyword
    │  - validate_scenario     │  ← checks output against ScenarioSpec schema
    │  - suggest_tools         │  ← returns relevant red/blue team tools
    └──────────────────────────┘
         │
         ▼
  Structured ScenarioSpec JSON
         │
         ▼
  Saved to /outputs/{slug}.json
```

---

# 4. Acceptance Criteria

- [x] Agent accepts a plain-language objective and returns valid JSON
- [x] Output passes Pydantic validation against `ScenarioSpec`
- [x] MITRE ATT&CK tactic IDs are real and relevant (from seed data)
- [x] Both red team and blue team sections are populated
- [x] Output is saved to `/outputs/` as a `.json` file
- [x] Works with either OpenAI (`gpt-4o`) or Anthropic (`claude-sonnet-4-6`)
- [x] Basic test coverage for schema validation and tool functions
- [x] Difficulty is inferred from the objective
- [ ] Agent should ask clarifying questions if the objective is too vague

---

## 5. Out of Scope (v1)

- No batch mode(multiple objectives at once) yet. This may be implemented in future development.
- No web UI (CLI only)
- No vector store / RAG (keep it simple first)
- No authentication
- No database persistence (file output is enough)

---

# 6. Tech Stack

| Layer             | Choice                                                     |
| ----------------- | ---------------------------------------------------------- |
| Language          | Python 3.11+                                               |
| Agent Framework   | LangChain                                                  |
| LLM               | OpenAI `gpt-4o` (default) or Anthropic `claude-sonnet-4-6` |
| Structured Output | Pydantic v2                                                |
| Seed Data         | MITRE ATT&CK tactics JSON (local file)                     |
| Testing           | pytest                                                     |

---

## 7. Resolved Decisions

- **Difficulty** — inferred by the LLM from the objective, not passed as a parameter
- **Clarifying questions** — deferred to v2; agent proceeds with any objective as given
- **Batch mode** — deferred to v2; noted in Out of Scope
- **`validate_scenario` return format** — returns a JSON string with a `status`
  field (`valid`, `invalid_schema`, `error`) rather than a plain string,
  enabling structured error handling and agent self-correction

---

## 8. v2 — RAG Enhancement: MITRE ATT&CK Technique Lookup

### Motivation

v1 uses a hand-crafted JSON file of 14 high-level MITRE ATT&CK tactics with
simple keyword matching. This limits scenario specificity — the agent can
reference "TA0006 Credential Access" but not "T1003.001 LSASS Memory" with
its associated detection guidance, data sources, and mitigations.

v2 replaces the tactic lookup tool with a RAG-powered technique lookup that
searches the full MITRE ATT&CK dataset (~200+ techniques) using semantic
similarity, returning richer, more actionable data for scenario generation.

---

### Data Source

MITRE ATT&CK STIX JSON from the official CTI repository:
`https://github.com/mitre/cti`

Specifically the Enterprise ATT&CK dataset:
`https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json`

This is ingested once via `scripts/build_index.py` and stored locally.
It is not re-fetched at runtime.

---

### Vector Store

**FAISS** (`faiss-cpu`) — local, file-based, no external service required.
Index is stored at `data/mitre_index/` and is gitignored.

Chosen for simplicity and portability on a single-developer project.
PGVector is the upgrade path if this moves to a hosted service.

---

### Embedding Model

**OpenAI `text-embedding-3-small`** via `langchain-openai`.
Requires `OPENAI_API_KEY` in `.env` — already present from v1.

Each MITRE technique is embedded as a concatenation of:

- Technique ID (e.g. `T1003.001`)
- Name (e.g. `LSASS Memory`)
- Description
- Detection guidance
- Tactic phase(s)

---

### New Tool: `lookup_mitre_technique`

Replaces `lookup_mitre_tactic` entirely.

```python
@tool
def lookup_mitre_technique(query: str) -> str:
    """Search the MITRE ATT&CK technique database using semantic similarity.
    Use this tool to find specific attack techniques, detection guidance,
    and mitigations relevant to the scenario being generated.
    Pass a natural language query such as 'credential dumping from memory'
    or 'lateral movement using remote services'.
    Returns the top 3 most relevant techniques with ID, name, tactic,
    description, detection, and mitigation fields.
    """
```

**Why it replaces rather than supplements `lookup_mitre_tactic`:**
Technique records include their parent tactic ID, so the new tool covers
both levels of the MITRE hierarchy. Maintaining two separate tools for
overlapping data would add unnecessary complexity and confusion for the agent.

---

### New File: `scripts/build_index.py`

A one-time ingestion script that:

1. Downloads the Enterprise ATT&CK STIX JSON from the mitre/cti repo
2. Parses and extracts technique objects (type: `attack-pattern`)
3. Filters out deprecated and revoked techniques
4. Embeds each technique using `text-embedding-3-small`
5. Saves the FAISS index to `data/mitre_index/`
6. Saves technique metadata (ID, name, tactic, detection, mitigation)
   to `data/mitre_index/techniques_metadata.json`

Run once before first use:

```bash
python scripts/build_index.py
```

---

### File Changes Summary

| File                          | Change                                                                      |
| ----------------------------- | --------------------------------------------------------------------------- |
| `scripts/build_index.py`      | New — one-time ingestion script                                             |
| `src/tools/rag_tool.py`       | New — `lookup_mitre_technique` tool                                         |
| `src/tools/scenario_tools.py` | Remove `lookup_mitre_tactic`, keep `validate_scenario` and `suggest_tools`  |
| `src/agent.py`                | Replace `lookup_mitre_tactic` with `lookup_mitre_technique` in tool list    |
| `src/prompts.py`              | Update system prompt to reference technique lookup instead of tactic lookup |
| `requirements.txt`            | Add `faiss-cpu`, update `langchain-openai`                                  |
| `data/mitre_index/`           | New gitignored directory — FAISS index lives here                           |
| `.gitignore`                  | Add `data/mitre_index/`                                                     |

---

### Acceptance Criteria (v2)

- [ ] `scripts/build_index.py` runs without error and produces a FAISS index
- [ ] `lookup_mitre_technique("credential dumping")` returns relevant techniques
      including T1003 and sub-techniques
- [ ] Agent uses technique IDs (T1xxx) in generated scenarios, not just
      tactic IDs (TAxxxx)
- [ ] Generated scenarios include detection guidance sourced from MITRE data
- [ ] `lookup_mitre_tactic` is removed and all tests updated accordingly
- [ ] All existing tests still pass
- [ ] New tests cover `lookup_mitre_technique` without hitting the OpenAI API
      (use a mock or pre-built test index)

---

### Out of Scope (v2)

- Sub-technique filtering by platform (Windows/Linux/macOS) — v3
- Automatic index refresh when MITRE releases updates — v3
- PGVector migration — future if project moves to hosted infrastructure
