"""
scripts/build_index.py

One-time ingestion script: downloads the MITRE ATT&CK Enterprise STIX dataset,
extracts technique objects, embeds them with OpenAI text-embedding-3-small, builds
a FAISS index, and saves both the index and technique metadata to data/mitre_index/.

Run once before first use:
    python scripts/build_index.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parents[1]
INDEX_DIR = PROJECT_ROOT / "data" / "mitre_index"
METADATA_PATH = INDEX_DIR / "techniques_metadata.json"

STIX_URL = (
    "https://raw.githubusercontent.com/mitre/cti/master/"
    "enterprise-attack/enterprise-attack.json"
)


def download_stix(url: str) -> dict:
    """Download the Enterprise ATT&CK STIX bundle from the mitre/cti repo."""
    print(f"[build_index] Downloading STIX bundle from:\n  {url}")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    print("[build_index] Download complete.")
    return response.json()


def extract_techniques(stix_bundle: dict) -> list[dict]:
    """Extract non-deprecated, non-revoked attack-pattern objects from the bundle."""
    objects = stix_bundle.get("objects", [])
    attack_patterns = [o for o in objects if o.get("type") == "attack-pattern"]
    print(f"[build_index] Total attack-pattern objects found: {len(attack_patterns)}")

    techniques = []
    for obj in attack_patterns:
        if obj.get("x_mitre_deprecated") is True or obj.get("revoked") is True:
            continue

        # Technique ID from external references
        technique_id = None
        for ref in obj.get("external_references", []):
            if ref.get("source_name") == "mitre-attack":
                technique_id = ref.get("external_id")
                break

        if not technique_id:
            continue  # skip objects without a resolvable ID

        # Tactic phases from kill chain
        tactic_phases: list[str] = [
            phase["phase_name"]
            for phase in obj.get("kill_chain_phases", [])
            if phase.get("kill_chain_name") == "mitre-attack"
        ]

        techniques.append(
            {
                "id": technique_id,
                "name": obj.get("name", ""),
                "tactics": tactic_phases,
                "description": obj.get("description", ""),
                "detection": obj.get("x_mitre_detection", ""),
            }
        )

    print(f"[build_index] Techniques after filtering deprecated/revoked: {len(techniques)}")
    return techniques


def build_embedding_texts(techniques: list[dict]) -> list[str]:
    """Concatenate each technique's fields into a single string for embedding."""
    texts = []
    for t in techniques:
        tactic_str = ", ".join(t["tactics"]) if t["tactics"] else "unknown"
        text = (
            f"{t['id']} {t['name']} "
            f"Tactics: {tactic_str} "
            f"Description: {t['description']} "
            f"Detection: {t['detection']}"
        )
        texts.append(text)
    return texts


def main() -> None:
    load_dotenv()

    # Ensure output directory exists
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Download STIX bundle
    stix_bundle = download_stix(STIX_URL)

    # 2 & 3. Extract and filter techniques
    techniques = extract_techniques(stix_bundle)

    if not techniques:
        print("[build_index] ERROR: No techniques extracted. Aborting.")
        sys.exit(1)

    # 4. Build embedding texts
    texts = build_embedding_texts(techniques)
    print(f"[build_index] Embedding {len(texts)} techniques with text-embedding-3-small...")

    # 5. Embed and build FAISS index
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    # Batch in groups of 100 to stay well within API rate limits
    batch_size = 100
    all_texts: list[str] = []
    all_metadatas: list[dict] = []

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_meta = techniques[i : i + batch_size]
        all_texts.extend(batch_texts)
        all_metadatas.extend(batch_meta)
        print(
            f"[build_index]   Prepared batch {i // batch_size + 1}/"
            f"{(len(texts) + batch_size - 1) // batch_size} "
            f"({min(i + batch_size, len(texts))}/{len(texts)} techniques)"
        )

    print("[build_index] Sending embeddings to OpenAI API...")
    vector_store = FAISS.from_texts(
        texts=all_texts,
        embedding=embeddings,
        metadatas=all_metadatas,
    )

    # 6. Save FAISS index
    vector_store.save_local(str(INDEX_DIR))
    print(f"[build_index] FAISS index saved to {INDEX_DIR}/")

    # 7. Save technique metadata as a standalone JSON list
    METADATA_PATH.write_text(json.dumps(techniques, indent=2))
    print(f"[build_index] Technique metadata saved to {METADATA_PATH}")
    print(f"[build_index] Done. {len(techniques)} techniques indexed.")


if __name__ == "__main__":
    main()
