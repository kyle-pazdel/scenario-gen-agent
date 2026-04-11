"""
src/tools/rag_tool.py

RAG-powered MITRE ATT&CK technique lookup tool using FAISS.

The FAISS index and technique metadata are loaded once at module level.
Run `scripts/build_index.py` before importing this module.
"""
from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parents[3]
_INDEX_DIR = _PROJECT_ROOT / "data" / "mitre_index"
_METADATA_PATH = _INDEX_DIR / "techniques_metadata.json"

# ---------------------------------------------------------------------------
# Module-level index and metadata load
# ---------------------------------------------------------------------------

_INDEX_NOT_BUILT_MSG = (
    "MITRE ATT&CK FAISS index not found. "
    "Please run `python scripts/build_index.py` to build the index before using this tool."
)

_vector_store = None
_techniques_by_id: dict[str, dict] = {}

def _load_index() -> None:
    """Load the FAISS index and technique metadata once at module import time."""
    global _vector_store, _techniques_by_id

    # Import here so the rest of the module doesn't fail if faiss isn't installed
    # in environments that don't need it (e.g. running v1-only tests).
    try:
        from langchain_community.vectorstores import FAISS
    except ImportError as exc:
        raise ImportError(
            "langchain-community and faiss-cpu are required for rag_tool. "
            "Run: pip install langchain-community faiss-cpu"
        ) from exc

    if not _INDEX_DIR.exists() or not any(_INDEX_DIR.iterdir()):
        raise FileNotFoundError(_INDEX_NOT_BUILT_MSG)

    if not _METADATA_PATH.exists():
        raise FileNotFoundError(
            f"Technique metadata not found at {_METADATA_PATH}. "
            "Please run `python scripts/build_index.py`."
        )

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    _vector_store = FAISS.load_local(
        folder_path=str(_INDEX_DIR),
        embeddings=embeddings,
        allow_dangerous_deserialization=True,
    )

    raw: list[dict] = json.loads(_METADATA_PATH.read_text())
    # Key by technique ID for fast lookup
    _techniques_by_id = {t["id"]: t for t in raw}


try:
    _load_index()
except FileNotFoundError:
    # Index hasn't been built yet — tool will return a helpful error at call time
    pass

# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

@tool
def lookup_mitre_technique(query: str) -> str:
    """Search the MITRE ATT&CK technique database using semantic similarity.

    Use this tool to find specific attack techniques, detection guidance, and
    mitigations relevant to the scenario being generated. Call it early in
    scenario generation to ground red team steps and blue team detection tasks
    in real MITRE technique data.

    Pass a natural language query describing the attacker behaviour or defensive
    concern you are researching. Examples:
      - 'credential dumping from memory'
      - 'lateral movement using remote services'
      - 'ransomware file encryption impact'
      - 'phishing initial access via email attachment'

    Returns the top 3 most relevant techniques, each containing:
      - id: MITRE technique ID (T1xxx or T1xxx.yyy sub-technique)
      - name: technique name
      - tactics: list of tactic phase names
      - description: what the technique does
      - detection: how defenders can detect it
    """
    if _vector_store is None:
        return json.dumps({"error": _INDEX_NOT_BUILT_MSG}, indent=2)

    docs = _vector_store.similarity_search(query=query, k=3)

    results: list[dict] = []
    for doc in docs:
        meta = doc.metadata
        technique_id = meta.get("id", "")
        # Prefer the richer metadata dict keyed by ID; fall back to FAISS metadata
        technique = _techniques_by_id.get(technique_id, meta)
        results.append(
            {
                "id": technique.get("id", technique_id),
                "name": technique.get("name", ""),
                "tactics": technique.get("tactics", []),
                "description": technique.get("description", ""),
                "detection": technique.get("detection", ""),
            }
        )

    return json.dumps(results, indent=2)
