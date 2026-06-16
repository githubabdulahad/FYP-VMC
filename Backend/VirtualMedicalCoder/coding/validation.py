"""Lightweight ICD/CPT validation for generated coding results.

This keeps the pipeline focused on the systems the project actually uses:
ICD-10-CM and CPT.

The validator is intentionally conservative:
- keep codes that match expected formats
- drop unsupported systems like SNOMED
- flag malformed codes for human review
"""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

ICD10_PATTERN = re.compile(r"^[A-TV-Z][0-9][A-Z0-9](?:\.[A-Z0-9]{1,4})?(?:[A-Z0-9]{0,2})?$")
CPT_PATTERN = re.compile(r"^[0-9]{4}[0-9A-Z]$")


class DatabaseCodingValidator:
    """Validate and normalize generated ICD/CPT codes against real databases."""

    def __init__(self):
        self.icd10_db = {}
        self.cpt_db = {}
        self._load_databases()
        # Precompute token sets for simple candidate search
        self.icd_tokens: dict[str, set[str]] = {}
        self.cpt_tokens: dict[str, set[str]] = {}
        self._build_token_index()

    def _load_databases(self):
        codes_dir = settings.BASE_DIR / "codes"

        # Load ICD-10
        icd_path = codes_dir / "icd-10.csv"
        try:
            with open(icd_path, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 5:
                        no_dot_code = row[2].strip().upper()
                        # Use column 4 (index 4) for full description, NOT column 3 (truncated)
                        desc = row[4].strip() if len(row) > 4 else row[3].strip()
                        self.icd10_db[no_dot_code] = desc
        except Exception as e:
            logger.error(f"Failed to load ICD-10 CSV: {e}")

        # Load CPT-4
        cpt_path = codes_dir / "cpt4.csv"
        try:
            with open(cpt_path, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # skip header
                for row in reader:
                    if len(row) >= 2:
                        self.cpt_db[row[0].strip().upper()] = row[1].strip()
        except Exception as e:
            logger.error(f"Failed to load CPT CSV: {e}")

    def _tokenize_text(self, text: str) -> set[str]:
        text = (text or "").lower()
        # keep alphanumeric tokens
        tokens = re.findall(r"[a-z0-9]+", text)
        return set(t for t in tokens if len(t) > 2)

    def _build_token_index(self):
        for code, desc in list(self.icd10_db.items()):
            self.icd_tokens[code] = self._tokenize_text(desc)
        for code, desc in list(self.cpt_db.items()):
            self.cpt_tokens[code] = self._tokenize_text(desc)

    def _score_candidate(self, evidence_tokens: set[str], candidate_tokens: set[str]) -> int:
        # simple overlap scoring
        return len(evidence_tokens & candidate_tokens)

    def search_icd_candidates(self, evidence: str, top_k: int = 5) -> list[dict[str, str]]:
        """Return top_k ICD-10 candidates (code, description, score) for evidence text."""
        if not evidence or not self.icd_tokens:
            return []
        ev_tokens = self._tokenize_text(evidence)
        scores = []
        for code, tokens in self.icd_tokens.items():
            score = self._score_candidate(ev_tokens, tokens)
            if score > 0:
                scores.append((score, code))
        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, code in scores[:top_k]:
            results.append({"code": code, "description": self.icd10_db.get(code, ""), "score": score})
        return results

    def search_cpt_candidates(self, evidence: str, top_k: int = 5) -> list[dict[str, str]]:
        """Return top_k CPT candidates (code, description, score) for evidence text."""
        if not evidence or not self.cpt_tokens:
            return []
        ev_tokens = self._tokenize_text(evidence)
        scores = []
        for code, tokens in self.cpt_tokens.items():
            score = self._score_candidate(ev_tokens, tokens)
            if score > 0:
                scores.append((score, code))
        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, code in scores[:top_k]:
            results.append({"code": code, "description": self.cpt_db.get(code, ""), "score": score})
        return results

    def find_best_icd_match(self, evidence: str) -> str | None:
        candidates = self.search_icd_candidates(evidence, top_k=1)
        return candidates[0]["code"] if candidates else None

    def find_best_cpt_match(self, evidence: str) -> str | None:
        candidates = self.search_cpt_candidates(evidence, top_k=1)
        return candidates[0]["code"] if candidates else None

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
        """Return (is_valid, reason, correct_description)."""
        code_upper = code.upper()

        if system == "ICD10":
            if not ICD10_PATTERN.match(code_upper):
                return False, "ICD-10 code format is invalid.", None
            
            if not self.icd10_db:
                return True, None, None

            no_dot = code_upper.replace(".", "")
            if no_dot in self.icd10_db:
                return True, None, self.icd10_db[no_dot]
            else:
                return False, f"ICD-10 code '{code}' not found in official database.", None

        if system == "CPT":
            if not CPT_PATTERN.match(code_upper):
                return False, "CPT code format is invalid.", None

            if not self.cpt_db:
                return True, None, None

            if code_upper in self.cpt_db:
                return True, None, self.cpt_db[code_upper]
            else:
                return False, f"CPT code '{code}' not found in official database.", None

        return False, f"Unsupported coding system: {system}", None

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
            
            # Z09 should NOT be used if:
            # 1. Patient has active/ongoing chronic conditions being treated (not post-treatment)
            chronic_conditions = ["copd", "diabetes", "hypertension", "asthma", "heart disease", 
                                 "chronic kidney disease", "ckd", "congestive heart failure", "chf"]
            
            # 2. Patient presenting with acute symptoms of existing condition
            active_treatment_keywords = [
                "treating", "managing", "continuing", "started on", "prescribed",
                "presents with", "complains of", "reports", "symptoms of",
                "acute", "exacerbation", "worsening", "worsened"
            ]
            
            # Check if any chronic condition is mentioned with active treatment language
            has_chronic_condition = any(cond in assessment for cond in chronic_conditions)
            has_active_treatment = any(keyword in assessment or keyword in plan 
                                      for keyword in active_treatment_keywords)
            
            # Check for post-treatment follow-up language
            post_treatment_keywords = [
                "follow-up after", "return for follow-up", "post-treatment",
                "post-op", "post-operative", "post-intervention", "after treatment",
                "check-up after", "evaluation after treatment completed"
            ]
            has_post_treatment_language = any(keyword in assessment or keyword in plan 
                                            for keyword in post_treatment_keywords)
            
            # Z09 is inappropriate if we have chronic disease with active treatment,
            # but no explicit post-treatment follow-up language
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
            has_screening_language = screening_keywords and any(kw in assessment for kw in screening_keywords)
            
            if not has_screening_language:
                return False, "Z12 (screening) should only be used when screening is explicitly documented"
        
        return True, None

    def validate_and_filter(self, llm_output: dict[str, Any]) -> dict[str, Any]:
        """Keep only ICD/CPT codes and attach DB validation logic."""
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
            
            # If the database has a canonical description, attach it
            if db_desc:
                normalized_item["db_description"] = db_desc

            # Additional Z-code validation for semantic appropriateness
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
