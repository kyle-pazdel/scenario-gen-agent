# Scenario Generation Agent - SPEC.md

> **This file is the source of truth for this project.**
> If the code and this spec disagree, fix the code.

---

## 1. What We're Building

A LangChain agent (Python) that accepts a high-level cybersecurity training objective and generates a fully structured scenario spec - including attacker steps, defender tasks, tools involved, and difficulty metadata.

This converts expert knowledge into deployable, structured training contetn at machine speed.

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

- [ ] Agent accepts a plain-language objective and returns valid JSON
- [ ] Output passes Pydantic validation against `ScenarioSpec`
- [ ] MITRE ATT&CK tactic IDs are real and relevant (from seed data)
- [ ] Both red team and blue team sections are populated
- [ ] Output is saved to `/outputs/` as a `.json` file
- [ ] Works with either OpenAI (`gpt-4o`) or Anthropic (`claude-sonnet-4-6`) as the LLM Backend
- [ ] Basic test coverage for schema validation and tool functions
- [ ] Agent should ask clarifying questions if the objective is too vague
- [ ] Difficulty should be inferred

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

## 7. Open Questions (resolve before coding)
