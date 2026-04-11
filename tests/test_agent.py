"""
Tests for scenario_schema models and scenario_tools LangChain tools.
No LLM calls are made — all tests run without any API key.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.scenario_schema import BlueTeam, Environment, RedTeam, ScenarioSpec
from src.tools.scenario_tools import suggest_tools, validate_scenario

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
# lookup_mitre_technique tool tests
# ---------------------------------------------------------------------------

# Sample technique dicts that stand in for real MITRE data
_FAKE_TECHNIQUES = [
    {
        "id": "T1003",
        "name": "OS Credential Dumping",
        "tactics": ["credential-access"],
        "description": "Adversaries may attempt to dump credentials to obtain account login information.",
        "detection": "Monitor for unexpected access to LSASS process memory.",
    },
    {
        "id": "T1003.001",
        "name": "LSASS Memory",
        "tactics": ["credential-access"],
        "description": "Adversaries may attempt to access credential material stored in LSASS memory.",
        "detection": "Monitor for access to the LSASS process using tools like Mimikatz.",
    },
    {
        "id": "T1021",
        "name": "Remote Services",
        "tactics": ["lateral-movement"],
        "description": "Adversaries may use valid accounts to log into remote services.",
        "detection": "Monitor authentication logs for unusual remote service access.",
    },
]


def _make_fake_doc(technique: dict) -> MagicMock:
    """Create a mock LangChain Document whose .metadata mirrors the technique dict."""
    doc = MagicMock()
    doc.metadata = technique
    return doc


class TestLookupMitreTechnique:
    """Tests for lookup_mitre_technique — no FAISS index or OpenAI API required."""

    def _invoke_with_mock_store(self, query: str, fake_docs: list) -> list[dict]:
        """
        Patch the module-level _vector_store inside rag_tool so similarity_search
        returns fake_docs, then invoke the tool and return the parsed JSON list.
        """
        import src.tools.rag_tool as rag_module
        from src.tools.rag_tool import lookup_mitre_technique

        mock_store = MagicMock()
        mock_store.similarity_search.return_value = fake_docs

        # Also patch _techniques_by_id so the tool can resolve metadata by ID
        fake_by_id = {t["id"]: t for t in _FAKE_TECHNIQUES}

        with patch.object(rag_module, "_vector_store", mock_store), \
             patch.object(rag_module, "_techniques_by_id", fake_by_id):
            result = lookup_mitre_technique.invoke({"query": query})

        return json.loads(result)

    def test_credential_dumping_returns_t1003(self):
        """Querying 'credential dumping' should return T1003 among the results."""
        fake_docs = [_make_fake_doc(_FAKE_TECHNIQUES[0]), _make_fake_doc(_FAKE_TECHNIQUES[1])]
        results = self._invoke_with_mock_store("credential dumping", fake_docs)
        ids = [r["id"] for r in results]
        assert "T1003" in ids

    def test_returns_at_most_three_results(self):
        """The tool must never return more than 3 results."""
        fake_docs = [_make_fake_doc(t) for t in _FAKE_TECHNIQUES]
        results = self._invoke_with_mock_store("any query", fake_docs)
        assert len(results) <= 3

    def test_result_contains_required_fields(self):
        """Every result dict must contain id, name, tactics, description, and detection."""
        fake_docs = [_make_fake_doc(_FAKE_TECHNIQUES[0])]
        results = self._invoke_with_mock_store("credential dumping", fake_docs)
        assert len(results) == 1
        result = results[0]
        for field in ("id", "name", "tactics", "description", "detection"):
            assert field in result, f"Missing field: {field}"

    def test_result_includes_detection_guidance(self):
        """The detection field must be populated — this is the key quality improvement over v1."""
        fake_docs = [_make_fake_doc(_FAKE_TECHNIQUES[0])]
        results = self._invoke_with_mock_store("credential dumping", fake_docs)
        assert results[0]["detection"] != ""

    def test_index_not_built_returns_error_message(self):
        """When the FAISS index hasn't been built, the tool should return a JSON error
        with a message directing the user to run scripts/build_index.py."""
        import src.tools.rag_tool as rag_module
        from src.tools.rag_tool import lookup_mitre_technique

        with patch.object(rag_module, "_vector_store", None):
            result = lookup_mitre_technique.invoke({"query": "credential dumping"})

        parsed = json.loads(result)
        assert "error" in parsed
        assert "build_index.py" in parsed["error"]


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
