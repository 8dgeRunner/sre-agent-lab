from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any


class TokenStore:
    """Persistent hashed Agent tokens; plaintext is returned only at issuance."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._records: dict[str, dict[str, Any]] = {}
        self._load()

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text())
            self._records = data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError):
            self._records = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._records, ensure_ascii=True, indent=2) + "\n")
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)

    ALLOWED_SCOPES = {"run:create", "evidence:read", "answer:submit"}
    DEFAULT_SCOPES = ["run:create", "evidence:read", "answer:submit"]

    def issue(self, name: str, *, ttl_days: int = 7, scopes: list[str] | None = None,
              owner: str = "", created_by: str = "") -> dict[str, Any]:
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError("token name must be 1-80 characters")
        owner = owner.strip()
        if len(owner) > 120:
            raise ValueError("owner must be at most 120 characters")
        if ttl_days < 1 or ttl_days > 90:
            raise ValueError("ttl_days must be between 1 and 90")
        requested_scopes = sorted(set(scopes or self.DEFAULT_SCOPES))
        if not requested_scopes or set(requested_scopes) - self.ALLOWED_SCOPES:
            raise ValueError("scopes contain unsupported permissions")
        # Hex avoids the '_' separator used in the token wire format.
        token_id = secrets.token_hex(8)
        token = f"sre_agent_{token_id}_{secrets.token_urlsafe(32)}"
        now = int(time.time())
        record = {
            "name": name, "owner": owner, "created_by": created_by,
            "hash": self._hash(token), "created_at": now,
            "expires_at": now + ttl_days * 86400, "revoked_at": None,
            "last_used_at": None, "use_count": 0, "scopes": requested_scopes,
        }
        with self._lock:
            self._records[token_id] = record
            self._save()
        return {"token_id": token_id, "token": token, **{key: value for key, value in record.items() if key != "hash"}}

    def verify(self, token: str, required_scope: str | None = None) -> bool:
        if not token.startswith("sre_agent_"):
            return False
        token_id = token.split("_", 3)[2] if len(token.split("_", 3)) > 2 else ""
        with self._lock:
            record = self._records.get(token_id)
            if not record or record.get("revoked_at") or int(record.get("expires_at", 0)) <= int(time.time()):
                return False
            if not secrets.compare_digest(str(record.get("hash", "")), self._hash(token)):
                return False
            if required_scope and required_scope not in record.get("scopes", []):
                return False
            record["last_used_at"] = int(time.time())
            record["use_count"] = int(record.get("use_count", 0)) + 1
            self._save()
            return True

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            now = int(time.time())
            result = []
            for token_id, record in sorted(self._records.items(), key=lambda item: item[1].get("created_at", 0), reverse=True):
                result.append({"token_id": token_id, **{key: value for key, value in record.items() if key != "hash"},
                               "status": "revoked" if record.get("revoked_at") else ("expired" if int(record.get("expires_at", 0)) <= now else "active")})
            return result

    def revoke(self, token_id: str) -> bool:
        with self._lock:
            record = self._records.get(token_id)
            if not record:
                return False
            record["revoked_at"] = int(time.time())
            self._save()
            return True
