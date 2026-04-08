import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from pydantic import ValidationError
from src.scenario_schema import ScenarioSpec

# Path to MITRE ATT&CK seed data relative to project root
_MITRE_TACTICS_PATH = Path(__file__).parents[2] / "data" / "mitre_tactics.json"

# Curated sets of common red and blue team tools by tactic/technique
_RED_TEAM_TOOLS: dict[str, list[str]] = {
    "initial access": ["Metasploit", "GoPhish", "SET (Social Engineering Toolkit)"],
    "execution": ["PowerShell Empire", "Cobalt Strike", "Sliver"],
    "persistence": ["Autoruns", "Scheduled Tasks", "Registry Run Keys"],
    "privilege escalation": ["Mimikatz", "BeRoot", "WinPEAS", "LinPEAS"],
    "defense evasion": ["Veil", "Obfuscation frameworks", "LOLBAS"],
    "credential access": ["Mimikatz", "LaZagne", "Responder", "Hashcat"],
    "discovery": ["Nmap", "BloodHound", "SharpHound", "ADRecon"],
    "lateral movement": ["PsExec", "Impacket", "WMIExec", "CrackMapExec"],
    "collection": ["WinRAR", "7-Zip", "Clipboard collectors"],
    "exfiltration": ["DNScat2", "Rclone", "custom exfiltration scripts"],
    "command and control": ["Cobalt Strike", "Sliver", "Havoc C2", "Metasploit"],
    "impact": ["custom encryptors", "WannaCry variants", "disk wipers"],
    "resource development": ["domain registrars", "VPS providers", "exploit kits"],
    "reconnaissance": ["Shodan", "Maltego", "theHarvester", "Recon-ng"],
    "ransomware": ["custom encryptor", "PsExec", "Mimikatz", "Cobalt Strike"],
    "phishing": ["GoPhish", "SET (Social Engineering Toolkit)", "Evilginx2"],
    "default": ["Metasploit", "Cobalt Strike", "Mimikatz", "Nmap", "Impacket"],
}

_BLUE_TEAM_TOOLS: dict[str, list[str]] = {
    "initial access": ["Splunk", "Microsoft Defender", "Proofpoint", "Email security gateways"],
    "execution": ["Sysmon", "Windows Event Logs", "CrowdStrike", "Carbon Black"],
    "persistence": ["Autoruns", "Sysinternals Suite", "KAPE", "Velociraptor"],
    "privilege escalation": ["Windows Event Logs", "Sysmon", "BloodHound", "PurpleSharp"],
    "defense evasion": ["Windows Defender", "CrowdStrike", "Carbon Black", "Sysmon"],
    "credential access": ["Windows Event Logs", "Sysmon", "Mimikatz detection tools", "Honeypots"],
    "discovery": ["Wireshark", "Zeek", "Network monitoring tools", "Sysmon"],
    "lateral movement": ["Windows Event Logs", "Sysmon", "Network segmentation", "Wireshark"],
    "collection": ["DLP solutions", "Windows Event Logs", "File integrity monitoring"],
    "exfiltration": ["Network monitoring", "DLP solutions", "Wireshark", "Zeek"],
    "command and control": ["Wireshark", "Suricata", "Snort", "Network firewalls"],
    "impact": ["Backup solutions", "File integrity monitoring", "Incident response tools"],
    "resource development": ["Threat intelligence platforms", "MISP", "VirusTotal"],
    "reconnaissance": ["Network monitoring", "Threat intelligence", "DNS monitoring"],
    "ransomware": ["Splunk", "Windows Event Logs", "Wireshark", "Velociraptor", "Sysmon"],
    "phishing": ["Proofpoint", "Microsoft Defender for Office 365", "URLScan.io"],
    "default": ["Splunk", "Wireshark", "Sysmon", "Velociraptor", "Windows Event Logs"],
}


@tool
def lookup_mitre_tactic(keyword: str) -> str:
    """Look up MITRE ATT&CK tactics that match a given keyword.

    Use this tool to find real MITRE ATT&CK tactic IDs and descriptions
    relevant to the scenario you are building. Pass a keyword such as
    'lateral movement', 'persistence', or 'exfiltration' to get matching
    tactic IDs and descriptions from the official seed data.

    Returns a JSON string listing all matching tactics with their ID, name,
    and description. If no match is found, all tactics are returned.
    """
    with open(_MITRE_TACTICS_PATH, "r") as f:
        tactics: dict[str, Any] = json.load(f)

    keyword_lower = keyword.lower()
    matches = {
        tactic_id: tactic_data
        for tactic_id, tactic_data in tactics.items()
        if keyword_lower in tactic_data["name"].lower()
        or keyword_lower in tactic_data["description"].lower()
    }

    result = matches if matches else tactics
    return json.dumps(result, indent=2)


@tool
def validate_scenario(scenario_json: str) -> str:
    """Validate a scenario JSON string against the ScenarioSpec Pydantic model.

    Use this tool before returning the final scenario to ensure the output is
    structurally correct and passes all schema constraints. Pass the raw JSON
    string of the scenario you have generated.

    This implementation handles JSON parse errors and Pydantic validation
    errors separately and returns structured JSON detailing the issue. Errors
    are marked as retryable where appropriate so the agent can attempt to
    correct and re-run generation.

    Returns a JSON string with keys: status, error_type (optional), message,
    details (optional), and retryable (bool).
    """
    # Attempt to parse JSON first
    try:
        parsed = json.loads(scenario_json)
    except json.JSONDecodeError as exc:
        return json.dumps({
            "status": "error",
            "error_type": "json_decode_error",
            "message": str(exc),
            "retryable": True,
        }, indent=2)

    # Validate using Pydantic
    try:
        ScenarioSpec.model_validate(parsed)
        return json.dumps({"status": "valid", "message": "Valid", "retryable": False}, indent=2)
    except ValidationError as ve:
        # Provide structured validation errors
        try:
            details = ve.errors()
        except Exception:
            details = str(ve)
        return json.dumps({
            "status": "invalid_schema",
            "error_type": "validation_error",
            "message": "Schema validation failed",
            "details": details,
            "retryable": True,
        }, indent=2)
    except Exception as exc:
        # Unknown errors should not halt the process but marked non-retryable
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": str(exc),
            "retryable": False,
        }, indent=2)


@tool
def suggest_tools(role: str, tactic_or_technique: str) -> str:
    """Suggest relevant security tools for a given role and tactic/technique.

    Use this tool to get a curated list of appropriate tools for red team
    (attacker) or blue team (defender) operations based on the MITRE ATT&CK
    tactic or specific technique being used.

    Args:
        role: Either 'red' for red team (attacker) tools or 'blue' for blue team (defender) tools
        tactic_or_technique: The MITRE ATT&CK tactic name or specific technique (e.g., 'lateral movement', 'ransomware', 'phishing')

    Returns a JSON list of recommended tool names for the specified role and tactic.
    """
    role_lower = role.lower()
    tactic_lower = tactic_or_technique.lower()

    if role_lower == "red":
        tools_dict = _RED_TEAM_TOOLS
    elif role_lower == "blue":
        tools_dict = _BLUE_TEAM_TOOLS
    else:
        return json.dumps({"error": f"Invalid role '{role}'. Use 'red' or 'blue'."})

    # Try to find exact match first
    if tactic_lower in tools_dict:
        tools = tools_dict[tactic_lower]
    else:
        # Try partial match
        matching_tools = []
        for key, tool_list in tools_dict.items():
            if key != "default" and (tactic_lower in key or key in tactic_lower):
                matching_tools.extend(tool_list)
        
        tools = matching_tools if matching_tools else tools_dict["default"]

    return json.dumps(tools, indent=2)