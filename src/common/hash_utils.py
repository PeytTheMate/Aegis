"""Canonical JSON and hashing helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any



def canonical_json_dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)



def sha256_json(payload: Any) -> str:
    digest = hashlib.sha256(canonical_json_dumps(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
