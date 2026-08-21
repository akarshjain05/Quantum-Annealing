"""
Tamper-evident audit chain (spec §33) - explicitly NOT called "blockchain".
Each event's hash incorporates the previous event's hash, so any historical
edit breaks the chain from that point forward and is detectable by
recomputation. This is a well-known append-only-log construction, not a
distributed consensus system.
"""
import hashlib
import json
from typing import Any, Dict, Optional

GENESIS_HASH = "0" * 64


def compute_hash(prev_hash: str, payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()


def verify_chain(entries) -> Dict[str, Any]:
    """entries: ordered list of objects with .prev_hash, .self_hash, and a
    dict-able payload. Recomputes each hash and confirms linkage."""
    expected_prev = GENESIS_HASH
    broken_at = None
    for entry in entries:
        if entry["prev_hash"] != expected_prev:
            broken_at = entry.get("id")
            break
        recomputed = compute_hash(entry["prev_hash"], entry["payload"])
        if recomputed != entry["self_hash"]:
            broken_at = entry.get("id")
            break
        expected_prev = entry["self_hash"]
    return {"valid": broken_at is None, "broken_at_id": broken_at, "entries_checked": len(entries)}
