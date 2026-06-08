from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import parse, request


@dataclass(slots=True)
class SupabaseClient:
    base_url: str
    service_key: str
    timeout_seconds: float = 10.0

    def _build_url(self, table: str, query_params: dict[str, str] | None = None) -> str:
        base = self.base_url.rstrip("/")
        endpoint = f"{base}/rest/v1/{table}"
        if not query_params:
            return endpoint

        return f"{endpoint}?{parse.urlencode(query_params)}"

    def _headers(self, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def upload_file(
        self,
        bucket: str,
        remote_path: str,
        file_path: str | Path,
        content_type: str = "image/jpeg",
    ) -> dict[str, Any]:
        base = self.base_url.rstrip("/")
        url = f"{base}/storage/v1/object/{bucket}/{remote_path}"
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": content_type,
            "Prefer": "return=representation",
        }
        
        file_bytes = Path(file_path).read_bytes()
        req = request.Request(url, data=file_bytes, headers=headers, method="POST")
        
        with request.urlopen(req, timeout=self.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return {}
            return json.loads(raw)

    def insert(
        self,
        table: str,
        rows: list[dict[str, Any]],
        *,
        on_conflict: str | None = None,
        prefer: str = "return=representation",
    ) -> list[dict[str, Any]]:
        params = {"on_conflict": on_conflict} if on_conflict else None
        url = self._build_url(table, params)
        body = json.dumps(rows).encode("utf-8")
        req = request.Request(url, data=body, headers=self._headers(prefer), method="POST")

        with request.urlopen(req, timeout=self.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return []
            return json.loads(raw)

    def select(
        self,
        table: str,
        *,
        query_params: dict[str, str],
    ) -> list[dict[str, Any]]:
        url = self._build_url(table, query_params)
        req = request.Request(url, headers=self._headers(), method="GET")

        with request.urlopen(req, timeout=self.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return []
            return json.loads(raw)

    def update(
        self,
        table: str,
        payload: dict[str, Any],
        *,
        query_params: dict[str, str],
    ) -> list[dict[str, Any]]:
        url = self._build_url(table, query_params)
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers=self._headers(prefer="return=representation"),
            method="PATCH",
        )

        with request.urlopen(req, timeout=self.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return []
            return json.loads(raw)

    def delete(
        self,
        table: str,
        *,
        query_params: dict[str, str],
    ) -> list[dict[str, Any]]:
        url = self._build_url(table, query_params)
        req = request.Request(
            url,
            headers=self._headers(prefer="return=representation"),
            method="DELETE",
        )

        with request.urlopen(req, timeout=self.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return []
            return json.loads(raw)
