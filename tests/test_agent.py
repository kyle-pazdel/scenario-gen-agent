"""
Tests for scenario_schema models and scenario_tools LangChain tools.
No LLM calls are made — all tests run without any API key.
"""
import json

import pytest
from pydantic import ValidationError

from src.scenario_schema import BlueTeam, Environment, RedTeam, ScenarioSpec
from src.tools.scenario_tools import lookup_mitre_tactic, suggest_tools, validate_scenario

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

VALID_SCENARIO_DICT = {
    "title": "Ransomware Detection & Response",
    "difficulty": "intermediate",
    "mitre_tactics": ["TA0001", "TA0002", "TA0008", "TA0040"],
    "red_team": {
        "objective": "Encrypt critical files and exfiltrate data before detection",
        "mitre_tactics": ["TA0002", "TA0008", "TA0040"],
        "steps": [
            "Establish initial access via phishing email",
            "Move laterally using PsExec",
            "Deploy ransomware payload to shared drives",
        ],
        "tools": ["Mimikatz", "PsExec", "custom encryptor"],
    },
    "blue_team": {
        "objective": "Detect the intrusion and contain the ransomware before full encryption",
        "mitre_tactics": ["TA0001", "TA0002", "TA0008", "TA0040"],
        "steps": [
            "Monitor SIEM for anomalous login activity",
            "Isolate affected host from network",
            "Recover files from backup",
        ],
        "tools": ["Splunk", "Windows Event Logs", "Wireshark"],
    },
    "environment": {
        "os": "Windows Server 2019",
        "network_topology": "flat corporate LAN with AD",
        "services": ["Active Directory", "SMB file shares", "RDP"],
    },
    "learning_objectives": [
        "Identify lateral movement indicators in Windows event logs",
        "Understand ransomware kill chain",
        "Practice incident containment procedures",
    ],
    "estimated_duration_minutes": 60,
}


# ---------------------------------------------------------------------------
# ScenarioSpec model tests
# ---------------------------------------------------------------------------


class TestScenarioSpec:
    def test_valid_scenario_passes_validation(self):
        """A complete, valid dict should deserialise into a ScenarioSpec without error."""
        scenario = ScenarioSpec.model_validate(VALID_SCENARIO_DICT)
        assert scenario.title == "Ransomware Detection & Response"
        assert scenario.difficulty == "intermediate"

    def test_invalid_difficulty_raises_validation_error(self):
        """A difficulty value outside the three allowed literals should raise ValidationError."""
        bad = {**VALID_SCENARIO_DICT, "difficulty": "expert"}
        with pytest.raises(ValidationError):
            ScenarioSpec.model_validate(bad)

    def test_missing_blue_team_raises_validation_error(self):
        """Omitting the required blue_team field should raise ValidationError."""
        bad = {k: v for k, v in VALID_SCENARIO_DICT.items() if k != "blue_team"}
        with pytest.raises(ValidationError):
            ScenarioSpec.model_validate(bad)


# ---------------------------------------------------------------------------
# lookup_mitre_tactic tool tests
# ---------------------------------------------------------------------------


class TestLookupMitreTactic:
    def test_lateral_movement_returns_ta0008(self):
        """Searching 'lateral movement' should include TA0008 in the result."""
        result = lookup_mitre_tactic.invoke({"keyword": "lateral movement"})
        data = json.loads(result)
        assert "TA0008" in data

    def test_nonsense_keyword_returns_all_tactics(self):
        """A keyword with no match should fall back to returning all 14 tactics."""
        result = lookup_mitre_tactic.invoke({"keyword": "xyzzy_nonexistent_keyword"})
        data = json.loads(result)
        # Seed data has 14 enterprise tactics
        assert len(data) == 14


# ---------------------------------------------------------------------------
# validate_scenario tool tests
# ---------------------------------------------------------------------------


class TestValidateScenario:
    def test_valid_scenario_json_returns_status_valid(self):
        """A well-formed, schema-compliant JSON string should return status == 'valid'."""
        scenario_json = json.dumps(VALID_SCENARIO_DICT)
        result = validate_scenario.invoke({"scenario_json": scenario_json})
        parsed = json.loads(result)
        assert parsed["status"] == "valid"

    def test_malformed_json_returns_error_status(self):
        """Passing malformed JSON should return a status indicating an error, not raise an exception."""
        result = validate_scenario.invoke({"scenario_json": "{this is not valid json"})
        parsed = json.loads(result)
        assert parsed["status"] in ("error", "invalid_schema")
        assert parsed.get("error_type") == "json_decode_error"
        assert parsed.get("retryable") is True

    def test_schema_violation_returns_invalid_schema_status(self):
        """Valid JSON that violates the schema should return status == 'invalid_schema'."""
        bad = {**VALID_SCENARIO_DICT, "difficulty": "ultra-hard"}
        result = validate_scenario.invoke({"scenario_json": json.dumps(bad)})
        parsed = json.loads(result)
        assert parsed["status"] == "invalid_schema"
        assert parsed.get("retryable") is True


# ---------------------------------------------------------------------------
# suggest_tools tool tests
# ---------------------------------------------------------------------------


class TestSuggestTools:
    def test_red_team_credential_access_includes_mimikatz(self):
        """Red team tools for 'credential access' should include Mimikatz."""
        result = suggest_tools.invoke({"role": "red", "tactic_or_technique": "credential access"})
        tools = json.loads(result)
        assert isinstance(tools, list)
        assert "Mimikatz" in tools

    def test_blue_team_ransomware_includes_splunk(self):
        """Blue team tools for 'ransomware' should include Splunk."""
        result = suggest_tools.invoke({"role": "blue", "tactic_or_technique": "ransomware"})
        tools = json.loads(result)
        assert isinstance(tools, list)
        assert "Splunk" in tools
