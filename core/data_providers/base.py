"""
Data Provider Layer (§17, §19 P2-17).

Pluggable adapter that routes keyword volume and domain authority queries to
whichever provider the subscriber has connected — DataForSEO → SEMrush → Ahrefs
for volume; Moz → Ahrefs → SEMrush for domain authority.

Agents call get_keyword_volume() / get_domain_authority() without knowing which
provider is active. Returns None silently if no key is configured.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ── Public API ─────────────────────────────────────────────────────────────────

def get_keyword_volume(keyword: str, user_id: int, db: "Session") -> dict | None:
    """
    Return keyword data from the first available provider.
    Priority: DataForSEO → SEMrush → Ahrefs.
    Returns {'volume': int, 'difficulty': float | None, 'source': str} or None.
    """
    from api.routers.identity.api_keys import get_user_secret
    from fastapi import HTTPException

    try:
        login = get_user_secret("dataforseo_login", user_id, db)
        password = get_user_secret("dataforseo_password", user_id, db)
        return _dataforseo_volume(keyword, login, password)
    except (HTTPException, Exception):
        pass

    try:
        key = get_user_secret("semrush_key", user_id, db)
        return _semrush_volume(keyword, key)
    except (HTTPException, Exception):
        pass

    try:
        key = get_user_secret("ahrefs_key", user_id, db)
        return _ahrefs_volume(keyword, key)
    except (HTTPException, Exception):
        pass

    return None


def get_domain_authority(domain: str, user_id: int, db: "Session") -> dict | None:
    """
    Return domain authority from the first available provider.
    Priority: Moz → Ahrefs → SEMrush.
    Returns {'da': int, 'source': str} or None.
    """
    from api.routers.identity.api_keys import get_user_secret
    from fastapi import HTTPException

    try:
        access_id = get_user_secret("moz_access_id", user_id, db)
        secret_key = get_user_secret("moz_secret_key", user_id, db)
        return _moz_da(domain, access_id, secret_key)
    except (HTTPException, Exception):
        pass

    try:
        key = get_user_secret("ahrefs_key", user_id, db)
        return _ahrefs_da(domain, key)
    except (HTTPException, Exception):
        pass

    try:
        key = get_user_secret("semrush_key", user_id, db)
        return _semrush_da(domain, key)
    except (HTTPException, Exception):
        pass

    return None


# ── DataForSEO ─────────────────────────────────────────────────────────────────

def _dataforseo_volume(keyword: str, login: str, password: str) -> dict | None:
    payload = [{"keywords": [keyword], "location_code": 2840, "language_code": "en"}]
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(
                "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live",
                json=payload,
                auth=(login, password),
            )
            r.raise_for_status()
            data = r.json()

        tasks = data.get("tasks") or []
        if not tasks or tasks[0].get("status_code") != 20000:
            return None
        result = (tasks[0].get("result") or [{}])[0]
        return {
            "volume": result.get("search_volume") or 0,
            "difficulty": None,
            "source": "dataforseo",
        }
    except Exception as e:
        logger.debug(f"DataForSEO volume error: {e}")
        return None


# ── SEMrush ────────────────────────────────────────────────────────────────────

def _semrush_volume(keyword: str, api_key: str) -> dict | None:
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(
                "https://api.semrush.com/",
                params={
                    "type": "phrase_this",
                    "key": api_key,
                    "phrase": keyword,
                    "database": "us",
                    "export_columns": "Ph,Nq,Kd",
                },
            )
            r.raise_for_status()
            lines = r.text.strip().splitlines()
        if len(lines) < 2:
            return None
        parts = lines[1].split(";")
        return {
            "volume": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
            "difficulty": float(parts[2]) if len(parts) > 2 else None,
            "source": "semrush",
        }
    except Exception as e:
        logger.debug(f"SEMrush volume error: {e}")
        return None


def _semrush_da(domain: str, api_key: str) -> dict | None:
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(
                "https://api.semrush.com/",
                params={
                    "type": "domain_rank",
                    "key": api_key,
                    "domain": domain,
                    "export_columns": "Dn,As",
                },
            )
            r.raise_for_status()
            lines = r.text.strip().splitlines()
        if len(lines) < 2:
            return None
        parts = lines[1].split(";")
        return {
            "da": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
            "source": "semrush",
        }
    except Exception as e:
        logger.debug(f"SEMrush DA error: {e}")
        return None


# ── Ahrefs ─────────────────────────────────────────────────────────────────────

def _ahrefs_volume(keyword: str, api_key: str) -> dict | None:
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(
                "https://api.ahrefs.com/v3/keywords-explorer/overview",
                params={"select": "volume,difficulty", "keywords": keyword, "country": "us"},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            r.raise_for_status()
            data = r.json()
        kw = (data.get("keywords") or [{}])[0]
        return {
            "volume": kw.get("volume") or 0,
            "difficulty": kw.get("difficulty"),
            "source": "ahrefs",
        }
    except Exception as e:
        logger.debug(f"Ahrefs volume error: {e}")
        return None


def _ahrefs_da(domain: str, api_key: str) -> dict | None:
    try:
        with httpx.Client(timeout=30) as client:
            r = client.get(
                "https://api.ahrefs.com/v3/site-explorer/domain-rating",
                params={"target": domain},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            r.raise_for_status()
            data = r.json()
        return {
            "da": int(data.get("domain_rating") or 0),
            "source": "ahrefs",
        }
    except Exception as e:
        logger.debug(f"Ahrefs DA error: {e}")
        return None


# ── Moz ────────────────────────────────────────────────────────────────────────

def _moz_da(domain: str, access_id: str, secret_key: str) -> dict | None:
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(
                "https://lsapi.seomoz.com/v2/url_metrics",
                json={"targets": [domain]},
                auth=(access_id, secret_key),
            )
            r.raise_for_status()
            data = r.json()
        results = data.get("results") or [{}]
        return {
            "da": int(results[0].get("domain_authority") or 0),
            "source": "moz",
        }
    except Exception as e:
        logger.debug(f"Moz DA error: {e}")
        return None
