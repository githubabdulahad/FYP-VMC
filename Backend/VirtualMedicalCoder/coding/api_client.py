"""
coding/api_client.py

Thin client for the NLM Clinical Table Search Service.

Endpoints used:
  ICD-10-CM : https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search
              → Free, government-backed, covers all ICD-10-CM codes.

  HCPCS L2  : https://clinicaltables.nlm.nih.gov/api/hcpcs/v3/search
              → Free. Covers HCPCS Level II codes (G, M, S, etc.).
              → DOES NOT cover CPT Level I (99xxx, etc.) — those are
                AMA-copyrighted and have no free public API.
                CPT validation falls back to the local cpt4.csv.

Response format (JSON array):
  [0] – total match count (int)
  [1] – list of matched code strings
  [2] – null
  [3] – list of [code, name] pairs matching the requested fields

Reference:
  ICD-10-CM: https://clinicaltables.nlm.nih.gov/apidoc/icd10cm/v3/doc.html
  HCPCS:     https://clinicaltables.nlm.nih.gov/apidoc/hcpcs/v3/doc.html
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — read from environment with sensible defaults
# ---------------------------------------------------------------------------
_BASE_URL: str = os.environ.get(
    "NLM_API_BASE_URL", "https://clinicaltables.nlm.nih.gov/api"
)
_TIMEOUT: float = float(os.environ.get("NLM_API_TIMEOUT", "5"))

_ICD10_ENDPOINT = f"{_BASE_URL}/icd10cm/v3/search"
_HCPCS_ENDPOINT = f"{_BASE_URL}/hcpcs/v3/search"

# Maximum results returned by NLM per query
_DEFAULT_MAX_LIST = 10


# ---------------------------------------------------------------------------
# Low-level HTTP helper
# ---------------------------------------------------------------------------

def _get(url: str, params: dict[str, Any]) -> list | None:
    """
    Perform a GET request to an NLM endpoint.

    Returns the parsed JSON list on success, None on any network/HTTP error.
    """
    try:
        response = requests.get(url, params=params, timeout=_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and len(data) >= 4:
            return data
        logger.warning("NLM API unexpected response shape from %s: %s", url, data)
        return None
    except RequestException as exc:
        logger.warning("NLM API request failed (%s): %s", url, exc)
        return None
    except ValueError as exc:
        logger.warning("NLM API JSON parse error (%s): %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# ICD-10-CM lookups
# ---------------------------------------------------------------------------

@lru_cache(maxsize=4096)
def lookup_icd10(code: str) -> tuple[bool, str | None]:
    """
    Check if an ICD-10-CM code exists in the NLM database.

    Args:
        code: ICD-10 code, with or without the dot (e.g. 'E11.9' or 'E119').

    Returns:
        (found, description) — description is None when not found.
    """
    # Normalise: NLM accepts dotted codes like E11.9
    normalised = _normalise_icd10(code)
    data = _get(_ICD10_ENDPOINT, {"terms": normalised, "sf": "code,name", "maxList": 5})
    if data is None:
        return False, None  # API unavailable — caller should use fallback

    pairs: list[list[str]] = data[3] or []
    for pair in pairs:
        if len(pair) >= 2 and pair[0].strip().upper() == normalised.upper():
            return True, pair[1].strip()
    return False, None


@lru_cache(maxsize=2048)
def search_icd10(text: str, top_k: int = 5) -> list[dict[str, str]]:
    """
    Search ICD-10-CM codes by free-text clinical term.

    Args:
        text: Clinical description (e.g. "type 2 diabetes mellitus").
        top_k: Maximum results to return.

    Returns:
        List of {"code": ..., "description": ...} dicts, ranked by relevance.
    """
    data = _get(
        _ICD10_ENDPOINT,
        {"terms": text, "sf": "code,name", "maxList": min(top_k, _DEFAULT_MAX_LIST)},
    )
    if data is None:
        return []

    pairs: list[list[str]] = data[3] or []
    results = []
    for pair in pairs[:top_k]:
        if len(pair) >= 2:
            results.append({"code": pair[0].strip(), "description": pair[1].strip()})
    return results


# ---------------------------------------------------------------------------
# HCPCS / CPT lookups
# ---------------------------------------------------------------------------

@lru_cache(maxsize=4096)
def lookup_cpt(code: str) -> tuple[bool, str | None]:
    """
    Check if a HCPCS Level II code exists in the NLM HCPCS database.

    IMPORTANT — Coverage:
      - This covers HCPCS Level II codes (G-codes, M-codes, S-codes, etc.)
      - It does NOT cover CPT Level I codes (99xxx, 12xxx, etc.) which are
        AMA-copyrighted and unavailable via any free public API.
      - For CPT Level I, callers should use the local cpt4.csv instead.

    Args:
        code: HCPCS code (e.g. 'G0438', 'M0064').

    Returns:
        (found, description).
        Returns (False, None) when not found OR when code is a CPT Level I code.
    """
    code_upper = code.strip().upper()

    # CPT Level I codes are all-numeric 5-digit (e.g. 99213, 12001).
    # NLM HCPCS endpoint won't have them — skip the network call.
    if code_upper.isdigit() and len(code_upper) == 5:
        return False, None

    data = _get(_HCPCS_ENDPOINT, {"terms": code_upper, "sf": "code,name", "maxList": 5})
    if data is None:
        return False, None  # API unavailable

    pairs: list[list[str]] = data[3] or []
    for pair in pairs:
        if len(pair) >= 2 and pair[0].strip().upper() == code_upper:
            return True, pair[1].strip()
    return False, None


@lru_cache(maxsize=2048)
def search_cpt(text: str, top_k: int = 5) -> list[dict[str, str]]:
    """
    Search HCPCS Level II codes by free-text clinical term.

    Note: This covers HCPCS Level II only (G-codes, M-codes etc.).
    CPT Level I (99xxx, 12xxx) are not available via free API — use
    the local cpt4.csv for those.

    Args:
        text: Clinical description.
        top_k: Maximum results to return.

    Returns:
        List of {"code": ..., "description": ...} dicts, or empty list
        if only CPT Level I codes are relevant.
    """
    data = _get(
        _HCPCS_ENDPOINT,
        {"terms": text, "sf": "code,name", "maxList": min(top_k, _DEFAULT_MAX_LIST)},
    )
    if data is None:
        return []

    pairs: list[list[str]] = data[3] or []
    results = []
    for pair in pairs[:top_k]:
        if len(pair) >= 2:
            results.append({"code": pair[0].strip(), "description": pair[1].strip()})
    return results


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _normalise_icd10(code: str) -> str:
    """
    Convert a no-dot ICD-10 code to dotted form for NLM lookup.

    E.g. 'E119' → 'E11.9', 'E1165' → 'E11.65', 'A001' → 'A00.1'
    Codes that already have a dot are returned as-is (uppercased).
    """
    code = code.strip().upper()
    if "." in code:
        return code
    # ICD-10-CM: first 3 chars are the category, remainder is the subcategory
    if len(code) > 3:
        return f"{code[:3]}.{code[3:]}"
    return code


def clear_caches() -> None:
    """Clear all in-process LRU caches (useful for testing)."""
    lookup_icd10.cache_clear()
    lookup_cpt.cache_clear()
    search_icd10.cache_clear()
    search_cpt.cache_clear()
