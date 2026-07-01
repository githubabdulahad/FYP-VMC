"""Lightweight ICD/CPT validation for generated coding results.

This keeps the pipeline focused on the systems the project actually uses:
ICD-10-CM and CPT.

Validation strategy (in priority order):
  1. NLM Clinical Table Search API  — authoritative, always up-to-date
  2. Local CSV fallback             — used when the API is unreachable
  3. Regex format check only        — used when both sources are unavailable

The validator is intentionally conservative:
- keep codes that match expected formats
- drop unsupported systems like SNOMED
- flag malformed codes for human review
"""

from __future__ import annotations

import csv
import logging
import os
import re
from pathlib import Path
from typing import Any

from django.conf import settings

# NLM API client — imported lazily so CSV-only startup still works
from coding import api_client

logger = logging.getLogger(__name__)

ICD10_PATTERN = re.compile(r"^[A-TV-Z][0-9][A-Z0-9](?:\.[A-Z0-9]{1,4})?(?:[A-Z0-9]{0,2})?$")
CPT_PATTERN = re.compile(r"^[0-9]{4}[0-9A-Z]$")

# Read from environment — default True so fallback is always on
_FALLBACK_TO_CSV: bool = os.environ.get("NLM_API_FALLBACK_TO_CSV", "True").lower() not in (
    "false", "0", "no"
)


class DatabaseCodingValidator:
    """Validate and normalize generated ICD/CPT codes.

    Primary source: NLM Clinical Table Search Service API.
    Fallback source: local ICD-10 and CPT-4 CSV files.
    """

    def __init__(self):
        # CSV databases — populated lazily only when the API is unavailable
        self.icd10_db: dict[str, str] = {}
        self.cpt_db: dict[str, str] = {}
        self._csv_loaded = False

        # Token indexes built from CSV data (used by CodeRetriever scoring)
        self.icd_tokens: dict[str, set[str]] = {}
        self.cpt_tokens: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # CSV fallback loading (lazy)
    # ------------------------------------------------------------------

    def _ensure_csv_loaded(self) -> None:
        """Load CSV databases on first access (lazy fallback)."""
        if self._csv_loaded:
            return
        self._csv_loaded = True  # set before loading to avoid re-entry on error
        self._load_databases()
        self._build_token_index()

    def _load_databases(self) -> None:
        codes_dir = settings.BASE_DIR / "codes"

        # Load ICD-10
        icd_path = codes_dir / "icd-10.csv"
        try:
            with open(icd_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 5:
                        no_dot_code = row[2].strip().upper()
                        desc = row[4].strip() if len(row) > 4 else row[3].strip()
                        self.icd10_db[no_dot_code] = desc
            logger.info("CSV fallback: loaded %d ICD-10 codes", len(self.icd10_db))
        except Exception as e:
            logger.error("Failed to load ICD-10 CSV fallback: %s", e)

        # Load CPT-4
        cpt_path = codes_dir / "cpt4.csv"
        try:
            with open(cpt_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)  # skip header
                for row in reader:
                    if len(row) >= 2:
                        self.cpt_db[row[0].strip().upper()] = row[1].strip()
            logger.info("CSV fallback: loaded %d CPT codes", len(self.cpt_db))
        except Exception as e:
            logger.error("Failed to load CPT CSV fallback: %s", e)

    def _tokenize_text(self, text: str) -> set[str]:
        text = (text or "").lower()
        tokens = re.findall(r"[a-z0-9]+", text)
        return set(t for t in tokens if len(t) > 2)

    def _build_token_index(self) -> None:
        for code, desc in self.icd10_db.items():
            self.icd_tokens[code] = self._tokenize_text(desc)
        for code, desc in self.cpt_db.items():
            self.cpt_tokens[code] = self._tokenize_text(desc)

    # ------------------------------------------------------------------
    # Candidate search — API first, CSV fallback
    # ------------------------------------------------------------------

    def search_icd_candidates(self, evidence: str, top_k: int = 5) -> list[dict[str, str]]:
        """Return top_k ICD-10 candidates for evidence text.

        Tries NLM API first; falls back to local CSV token search.
        """
        if not evidence:
            return []

        # --- Primary: NLM API ---
        api_results = api_client.search_icd10(evidence, top_k=top_k)
        if api_results:
            logger.debug("ICD-10 search via NLM API: %d results for '%s'", len(api_results), evidence[:60])
            return [
                {"code": r["code"], "description": r["description"], "score": idx + 1}
                for idx, r in enumerate(api_results)
            ]

        # --- Fallback: CSV token search ---
        if _FALLBACK_TO_CSV:
            logger.warning("NLM API unavailable for ICD search — using CSV fallback")
            self._ensure_csv_loaded()
            return self._csv_search_icd(evidence, top_k)

        return []

    def search_cpt_candidates(self, evidence: str, top_k: int = 5) -> list[dict[str, str]]:
        """Return top_k CPT candidates for evidence text.

        Tries NLM API first; falls back to local CSV token search.
        """
        if not evidence:
            return []

        # --- Primary: NLM API ---
        api_results = api_client.search_cpt(evidence, top_k=top_k)
        if api_results:
            logger.debug("CPT search via NLM API: %d results for '%s'", len(api_results), evidence[:60])
            return [
                {"code": r["code"], "description": r["description"], "score": idx + 1}
                for idx, r in enumerate(api_results)
            ]

        # --- Fallback: CSV token search ---
        if _FALLBACK_TO_CSV:
            logger.warning("NLM API unavailable for CPT search — using CSV fallback")
            self._ensure_csv_loaded()
            return self._csv_search_cpt(evidence, top_k)

        return []

    def _score_candidate(self, evidence_tokens: set[str], candidate_tokens: set[str]) -> int:
        return len(evidence_tokens & candidate_tokens)

    def _csv_search_icd(self, evidence: str, top_k: int) -> list[dict[str, str]]:
        if not self.icd_tokens:
            return []
        ev_tokens = self._tokenize_text(evidence)
        scores = [
            (self._score_candidate(ev_tokens, tokens), code)
            for code, tokens in self.icd_tokens.items()
            if self._score_candidate(ev_tokens, tokens) > 0
        ]
        scores.sort(key=lambda x: x[0], reverse=True)
        return [
            {"code": code, "description": self.icd10_db.get(code, ""), "score": score}
            for score, code in scores[:top_k]
        ]

    def _csv_search_cpt(self, evidence: str, top_k: int) -> list[dict[str, str]]:
        if not self.cpt_tokens:
            return []
        ev_tokens = self._tokenize_text(evidence)
        scores = [
            (self._score_candidate(ev_tokens, tokens), code)
            for code, tokens in self.cpt_tokens.items()
            if self._score_candidate(ev_tokens, tokens) > 0
        ]
        scores.sort(key=lambda x: x[0], reverse=True)
        return [
            {"code": code, "description": self.cpt_db.get(code, ""), "score": score}
            for score, code in scores[:top_k]
        ]

    def find_best_icd_match(self, evidence: str) -> str | None:
        candidates = self.search_icd_candidates(evidence, top_k=1)
        return candidates[0]["code"] if candidates else None

    def find_best_cpt_match(self, evidence: str) -> str | None:
        candidates = self.search_cpt_candidates(evidence, top_k=1)
        return candidates[0]["code"] if candidates else None

    # ------------------------------------------------------------------
    # Code validation — API first, CSV fallback, regex last resort
    # ------------------------------------------------------------------

    def normalize_system(self, raw_system: Any) -> str | None:
        if raw_system is None:
            return None
        value = str(raw_system).strip().upper().replace("-", "").replace(" ", "")
        mapping = {
            "ICD10": "ICD10",
            "ICD": "ICD10",
            "CPT": "CPT",
        }
        return mapping.get(value)

    def validate_code(self, system: str, code: str) -> tuple[bool, str | None, str | None]:
        """Return (is_valid, reason, correct_description).

        Lookup order:
          1. NLM API (primary)
          2. Local CSV (fallback, if NLM unavailable)
          3. Regex format check only (if both unavailable)
        """
        code_upper = code.upper()

        if system == "ICD10":
            # Format check first (fast, no I/O)
            if not ICD10_PATTERN.match(code_upper):
                return False, "ICD-10 code format is invalid.", None

            # --- Primary: NLM API ---
            found, desc = api_client.lookup_icd10(code_upper)
            if found:
                logger.debug("ICD-10 API lookup: %s → found", code_upper)
                return True, None, desc
            if desc is None:
                # API returned None → it was unreachable (not "not found")
                logger.warning("NLM API unreachable for ICD-10 lookup of %s", code_upper)
                if _FALLBACK_TO_CSV:
                    return self._csv_validate_icd10(code_upper)
                # No fallback: accept format-valid codes with a warning
                logger.warning("Accepting %s based on format only (no API, no CSV)", code_upper)
                return True, None, None

            # API reachable but code not found
            return False, f"ICD-10 code '{code}' not found in official NLM database.", None

        if system == "CPT":
            if not CPT_PATTERN.match(code_upper):
                return False, "CPT code format is invalid.", None

            # --- CPT Level I (5-digit numeric e.g. 99213): CSV is primary ---
            # There is no free public API for AMA-copyrighted CPT Level I codes.
            # Use the local cpt4.csv as the authoritative source.
            is_cpt_level1 = code_upper.isdigit() and len(code_upper) == 5

            if is_cpt_level1:
                self._ensure_csv_loaded()
                if self.cpt_db:
                    return self._csv_validate_cpt(code_upper)
                # CSV unavailable — accept on format only
                logger.warning("CPT CSV unavailable for %s — accepting on format", code_upper)
                return True, None, None

            # --- HCPCS Level II (alphanumeric e.g. G0438): try NLM API ---
            found, desc = api_client.lookup_cpt(code_upper)
            if found:
                logger.debug("HCPCS API lookup: %s → found", code_upper)
                return True, None, desc
            if desc is None:
                # API unreachable — try CSV
                if _FALLBACK_TO_CSV:
                    return self._csv_validate_cpt(code_upper)
                return True, None, None

            return False, f"HCPCS code '{code}' not found in NLM HCPCS database.", None

        return False, f"Unsupported coding system: {system}", None

    def _csv_validate_icd10(self, code_upper: str) -> tuple[bool, str | None, str | None]:
        """Validate ICD-10 against local CSV."""
        self._ensure_csv_loaded()
        if not self.icd10_db:
            logger.warning("CSV fallback also unavailable for ICD-10 %s — accepting on format", code_upper)
            return True, None, None
        no_dot = code_upper.replace(".", "")
        if no_dot in self.icd10_db:
            logger.debug("ICD-10 CSV fallback: %s → found", code_upper)
            return True, None, self.icd10_db[no_dot]
        return False, f"ICD-10 code '{code_upper}' not found in local CSV database.", None

    def _csv_validate_cpt(self, code_upper: str) -> tuple[bool, str | None, str | None]:
        """Validate CPT against local CSV."""
        self._ensure_csv_loaded()
        if not self.cpt_db:
            logger.warning("CSV fallback also unavailable for CPT %s — accepting on format", code_upper)
            return True, None, None
        if code_upper in self.cpt_db:
            logger.debug("CPT CSV fallback: %s → found", code_upper)
            return True, None, self.cpt_db[code_upper]
        return False, f"CPT code '{code_upper}' not found in local CSV database.", None

    # ------------------------------------------------------------------
    # Z-code semantic validation (unchanged)
    # ------------------------------------------------------------------

    def _check_z_code_appropriateness(self, z_code: str, llm_output: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate that Z-codes are used appropriately based on clinical context.

        Returns: (is_appropriate, reason_if_inappropriate)
        """
        z_code_upper = z_code.upper()

        # Z09 - Follow-up examination after completed treatment
        if z_code_upper == "Z09":
            soap_note = llm_output.get("soap_note", {})
            assessment = (soap_note.get("assessment") or "").lower()
            plan = (soap_note.get("plan") or "").lower()

            chronic_conditions = ["copd", "diabetes", "hypertension", "asthma", "heart disease",
                                 "chronic kidney disease", "ckd", "congestive heart failure", "chf"]

            active_treatment_keywords = [
                "treating", "managing", "continuing", "started on", "prescribed",
                "presents with", "complains of", "reports", "symptoms of",
                "acute", "exacerbation", "worsening", "worsened"
            ]

            post_treatment_keywords = [
                "follow-up after", "return for follow-up", "post-treatment",
                "post-op", "post-operative", "post-intervention", "after treatment",
                "check-up after", "evaluation after treatment completed"
            ]

            has_chronic_condition = any(cond in assessment for cond in chronic_conditions)
            has_active_treatment = any(
                keyword in assessment or keyword in plan
                for keyword in active_treatment_keywords
            )
            has_post_treatment_language = any(
                keyword in assessment or keyword in plan
                for keyword in post_treatment_keywords
            )

            if has_chronic_condition and has_active_treatment and not has_post_treatment_language:
                return False, (
                    "Z09 (follow-up after completed treatment) is inappropriate for ongoing "
                    "active management of chronic conditions. Use only when explicitly documented "
                    "as follow-up after treatment completion."
                )

        # Z12 - Screening for condition
        elif z_code_upper.startswith("Z12"):
            soap_note = llm_output.get("soap_note", {})
            assessment = (soap_note.get("assessment") or "").lower()
            screening_keywords = ["screening", "screen for", "screened for", "preventive"]
            has_screening_language = any(kw in assessment for kw in screening_keywords)
            if not has_screening_language:
                return False, "Z12 (screening) should only be used when screening is explicitly documented"

        return True, None

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def validate_and_filter(self, llm_output: dict[str, Any]) -> dict[str, Any]:
        """Keep only ICD/CPT codes and attach validation results."""
        validated_codes: list[dict[str, Any]] = []
        validation_report: list[dict[str, Any]] = []
        needs_human_review = False

        for item in llm_output.get("codes", []):
            if not isinstance(item, dict):
                continue

            system = self.normalize_system(item.get("system"))
            code = str(item.get("code", "")).strip()
            if system not in {"ICD10", "CPT"} or not code:
                continue

            is_valid, reason, db_desc = self.validate_code(system, code)
            normalized_item = item.copy()
            normalized_item["system"] = system
            normalized_item["code"] = code

            if db_desc:
                normalized_item["db_description"] = db_desc

            # Additional Z-code validation
            if is_valid and system == "ICD10" and code.upper().startswith("Z"):
                z_appropriate, z_reason = self._check_z_code_appropriateness(code, llm_output)
                if not z_appropriate:
                    is_valid = False
                    reason = z_reason

            if not is_valid:
                needs_human_review = True
                normalized_item["needs_review"] = True
                normalized_item["review_reason"] = reason
                validation_report.append(
                    {
                        "system": system,
                        "code": code,
                        "action": "flag_for_review",
                        "issues": [reason],
                    }
                )

            validated_codes.append(normalized_item)

        result = llm_output.copy()
        result["codes"] = validated_codes
        result["validation_report"] = validation_report
        result["needs_human_review"] = needs_human_review
        result["validation_summary"] = {
            "total_codes": len(validated_codes),
            "flagged_for_review": sum(1 for c in validated_codes if c.get("needs_review")),
            "clean": sum(1 for c in validated_codes if not c.get("needs_review")),
        }
        return result


validator = DatabaseCodingValidator()
