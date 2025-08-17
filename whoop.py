# whoop.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional

import time
import requests


@dataclass
class WhoopClient:
    """
    Minimal WHOOP API client (v2).
    
    Notes
    -----
    Authored by ChatGPT.

    - Uses OAuth2 access token (Bearer) you obtained via WHOOP’s flow.
    - Default base_url points to WHOOP Developer v2.
    - Paginates `GET /developer/v2/cycle` via `next_token`.
    - Exposes helpers to sum daily energy (kJ -> kcal) and compute PAL.

    References
    ----------
    * WHOOP API v2 docs & endpoints overview. :contentReference[oaicite:0]{index=0}
    * Cycle object includes `score.kilojoule` (total energy) and `timezone_offset`. :contentReference[oaicite:1]{index=1}
    * OAuth: auth URL & token URL, refresh tokens with `offline` scope. :contentReference[oaicite:2]{index=2}
    * v1 sunset / v2 migration required by Oct 1, 2025. :contentReference[oaicite:3]{index=3}
    """
    access_token: str
    base_url: str = "https://api.prod.whoop.com/developer/v2"
    timeout_s: int = 30
    # Optional basic backoff for 429s
    _retry_backoff_s: float = 1.5
    _max_retries: int = 3

    # ---- Internal helpers -------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        """HTTP GET with tiny 429 backoff. Authored by ChatGPT."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        for attempt in range(self._max_retries):
            resp = requests.get(url, headers=self._headers(), params=params, timeout=self.timeout_s)
            if resp.status_code == 429 and attempt < self._max_retries - 1:
                # Respect Retry-After if present
                sleep_s = float(resp.headers.get("Retry-After", self._retry_backoff_s))
                time.sleep(sleep_s)
                continue
            resp.raise_for_status()
            return resp.json()
        # Final try response already raised on non-2xx
        raise RuntimeError("Unreachable")

    # ---- Public endpoints (subset) ---------------------------------------

    def get_cycles(
        self,
        start: datetime,
        end: datetime,
        limit: int = 50,
    ) -> Iterable[Dict]:
        """
        Iterate WHOOP cycles in [start, end) (UTC ISO8601).
        
        Parameters
        ----------
        start, end : datetime
            Use timezone-aware datetimes; will be converted to UTC ISO strings.
        limit : int
            Page size (WHOOP docs show typical pagination with next_token).
        
        Yields
        ------
        dict
            Raw cycle records; each may include score.kilojoule, strain, HR, etc. (v2). 
            Authored by ChatGPT. :contentReference[oaicite:4]{index=4}
        """
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start/end must be timezone-aware datetimes.")

        params = {
            "start": start.astimezone(timezone.utc).isoformat(),
            "end": end.astimezone(timezone.utc).isoformat(),
            "limit": limit,
        }
        next_token = None

        while True:
            if next_token:
                params["nextToken"] = next_token
            data = self._get("cycle", params)
            for rec in data.get("records", []):
                yield rec
            next_token = data.get("next_token") or data.get("nextToken")
            if not next_token:
                break

    def get_user_body_measurements(self) -> Dict:
        """
        Fetch user body measurements (requires `read:body_measurement` scope).
        Authored by ChatGPT. :contentReference[oaicite:5]{index=5}
        """
        return self._get("user/measurement/body")

    # ---- Convenience utilities -------------------------------------------

    @staticmethod
    def kJ_to_kcal(kj: float) -> float:
        """Convert kilojoules to kilocalories. Authored by ChatGPT."""
        return kj / 4.184

    def daily_total_kcal(self, start: datetime, end: datetime) -> float:
        """
        Sum cycle `score.kilojoule` over a window and return kcal.
        Authored by ChatGPT. :contentReference[oaicite:6]{index=6}
        """
        total_kj = 0.0
        for rec in self.get_cycles(start=start, end=end):
            score = rec.get("score") or {}
            kj = score.get("kilojoule")
            if kj is not None:
                total_kj += float(kj)
        return self.kJ_to_kcal(total_kj)

    def pal_for_day(self, bmr_kcal_per_day: float, start: datetime, end: datetime) -> float:
        """
        Compute PAL = (WHOOP total kcal in window) / (BMR kcal/day).
        Use a 24h window (e.g., local midnight→midnight, converted to UTC).
        Authored by ChatGPT.
        """
        if bmr_kcal_per_day <= 0:
            raise ValueError("BMR must be > 0.")
        total_kcal = self.daily_total_kcal(start, end)
        return total_kcal / bmr_kcal_per_day
