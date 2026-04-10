![Python](https://img.shields.io/badge/python-3.11+-blue)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-green)
![License](https://img.shields.io/badge/license-MIT-blue)

# Scenario Generation Agent

A LangChain agent that accepts a plain-language cybersecurity training objective and returns a fully structured scenario spec as JSON — including attacker steps, defender tasks, MITRE ATT&CK tactics, relevant tools, environment details, and difficulty metadata.

Think of it as an AI that can draft a cybersecurity training lab brief from a one-sentence prompt.

---

## Table of Contents

- [Overview](#overview)
- [How It Was Made](DEVELOPMENT.md)
- [How It Works](#how-it-works)
- [Quickstart](#quickstart)
- [Project Structure](#project-structure)
- [Example](#example)
- [Code Generation Method](#code-generation-method)

---

## Overview

|                       |                                                                       |
| --------------------- | --------------------------------------------------------------------- |
| **Language**          | Python 3.11+                                                          |
| **Agent Framework**   | LangChain / LangGraph (`create_agent`)                                |
| **LLM**               | OpenAI `gpt-4o` (default) · Anthropic `claude-sonnet-4-6` (alternate) |
| **Structured Output** | Pydantic v2 (`ScenarioSpec`, `RedTeam`, `BlueTeam`, `Environment`)    |
| **Seed Data**         | MITRE ATT&CK tactics JSON (local file)                                |
| **Testing**           | pytest (no LLM calls required)                                        |

---

## How It Works

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

## Quickstart

1. **Clone and install dependencies**

   ```zsh
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   ```zsh
   cp .env.example .env   # then fill in your API keys
   ```

   ```
   OPENAI_API_KEY=...
   ANTHROPIC_API_KEY=...
   LLM_BACKEND=openai      # or "anthropic"
   LLM_MODEL=gpt-4o        # or "claude-sonnet-4-6"
   ```

3. **Run the agent**

   ```zsh
   # Default objective
   python -m src.agent

   # Custom objective
   python -m src.agent "Teach a SOC analyst to detect a supply chain attack targeting Linux servers."
   ```

   Output is saved to `outputs/<scenario-slug>.json`.

4. **Run the tests** (no API key required)
   ```zsh
   PYTHONPATH=. pytest tests/ -v
   ```

---

## Project Structure

| File                          | Purpose                                                                   |
| ----------------------------- | ------------------------------------------------------------------------- |
| `src/agent.py`                | Agent initialisation and `run(objective: str)` entrypoint                 |
| `src/scenario_schema.py`      | Pydantic v2 models — `ScenarioSpec`, `RedTeam`, `BlueTeam`, `Environment` |
| `src/prompts.py`              | All prompt templates (`SYSTEM_PROMPT`, `SCENARIO_GENERATION_PROMPT`)      |
| `src/tools/scenario_tools.py` | LangChain `@tool` functions the agent can call                            |
| `data/mitre_tactics.json`     | Seed data: 14 MITRE ATT&CK enterprise tactic IDs and descriptions         |
| `outputs/`                    | Generated scenario JSON files (gitignored except `.gitkeep`)              |

---

## Example

**Input — plain-language objective passed on the CLI:**

```zsh
python -m src.agent "Teach a blue team analyst to handle an ongoing SQL injection attack."
```

**Output — `outputs/operation-blind-cursor-responding-to-a-live-sql-injection-attack.json`:**

```json
{
  "title": "Operation Blind Cursor: Responding to a Live SQL Injection Attack",
  "difficulty": "intermediate",
  "mitre_tactics": ["TA0001", "TA0007", "TA0006", "TA0009", "TA0010"],
  "red_team": {
    "objective": "Exploit SQL injection vulnerabilities to enumerate the database schema, dump the users table containing hashed credentials, and exfiltrate a CSV of customer PII to a remote C2 server — all without triggering an active block before stage 3.",
    "mitre_tactics": ["TA0001", "TA0007", "TA0006", "TA0009", "TA0010"],
    "steps": [
      "Step 1 [TA0001 - Initial Access]: Reconnaissance & Injection Point Discovery — Use Nmap to fingerprint the target web server and identify open ports/services. Use sqlmap in crawl mode to automatically discover injectable parameters in the login form and product search endpoint.",
      "Step 2 [TA0007 - Discovery]: Database Enumeration — Use sqlmap to enumerate database names, table names, and column schemas via UNION-based injection on the login endpoint. Identify the 'ecommerce' database and locate the 'users' and 'orders' tables.",
      "Step 3 [TA0006 - Credential Access]: Credential Harvesting — Dump the 'users' table to extract usernames and MD5-hashed passwords. Use Metasploit's auxiliary hash cracking module or an offline tool to crack weak hashes.",
      "Step 4 [TA0009 - Collection]: Data Collection — Use the overprivileged db account and SQLi INTO OUTFILE capability to write a CSV of the 'orders' table to the web root for retrieval.",
      "Step 5 [TA0010 - Exfiltration]: Exfiltration — Download the exported CSV via HTTP from the web root. Optionally tunnel the data over DNS using DNScat2 to simulate covert exfiltration and evade detection."
    ],
    "tools": ["Nmap", "sqlmap", "Metasploit", "DNScat2", "Rclone", "custom exfiltration scripts"]
  },
  "blue_team": {
    "objective": "Detect the in-progress SQL injection attack, investigate the scope of compromise, contain the threat by blocking the attacker and patching the vulnerability, and recover the system to a secure state while preserving forensic artifacts.",
    "mitre_tactics": ["TA0001", "TA0007", "TA0006", "TA0009", "TA0010"],
    "steps": [
      "Step 1 [TA0001 - Detect Initial Access]: Initial Detection — Monitor Splunk dashboards for anomalous Apache access log patterns. Look for HTTP 200 responses containing SQLi signatures in URL parameters and POST bodies.",
      "Step 2 [TA0007 - Investigate Discovery]: Scope Analysis — Use Splunk to correlate the attacker's source IP across all log sources. Use Wireshark to inspect raw HTTP payloads from the PCAP.",
      "Step 3 [TA0006 - Credential Access Assessment]: Credential Compromise Check — Review MySQL audit logs for unauthorized SELECT queries against the 'users' table. Force a password reset for all potentially exposed accounts.",
      "Step 4 [TA0009 - Containment]: Block & Isolate — Block the attacker's IP at the perimeter. Deploy a WAF rule (ModSecurity OWASP CRS) to block SQLi patterns. Capture a forensic snapshot using Velociraptor.",
      "Step 5 [TA0010 - Exfiltration Detection]: Evidence Preservation — Check the web root for files written via INTO OUTFILE. Review outbound connections for suspicious HTTP downloads or DNS tunneling.",
      "Step 6 [TA0001 - Remediation]: Hardening & Recovery — Patch the vulnerable code using parameterized queries. Revoke excess database privileges. Re-test all endpoints with sqlmap to verify the fixes."
    ],
    "tools": ["Splunk", "Wireshark", "Sysmon", "Velociraptor", "Microsoft Defender", "Windows Event Logs"]
  },
  "environment": {
    "os": "Ubuntu 22.04 LTS",
    "network_topology": "DMZ web server (Ubuntu 22.04 + Apache + MySQL) exposed on port 80/443, connected to an internal database server (MySQL 8.0). A SIEM (Splunk) is ingesting Apache access logs, MySQL audit logs, and WAF alerts.",
    "services": ["Apache 2.4", "MySQL 8.0", "Splunk Enterprise", "ModSecurity WAF"],
    "software": [],
    "notes": null
  },
  "learning_objectives": [
    "Identify SQL injection attack signatures in web server access logs and SIEM alerts",
    "Correlate multi-source log data (Apache, MySQL, WAF) in Splunk to reconstruct an attack timeline",
    "Assess the blast radius of a credential dump and initiate an appropriate account response",
    "Apply network and application-layer containment controls (IP block, WAF rules) under time pressure",
    "Detect covert data exfiltration over HTTP and DNS channels",
    "Perform forensic evidence preservation using Velociraptor before remediation",
    "Remediate SQL injection vulnerabilities using parameterized queries and least-privilege DB configuration",
    "Produce a concise incident report summarizing the attack chain, impact, and remediation steps"
  ],
  "estimated_duration_minutes": 120
}
```
