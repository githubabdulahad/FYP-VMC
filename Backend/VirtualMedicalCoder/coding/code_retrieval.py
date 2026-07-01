"""
coding/code_retrieval.py

Evidence-based code retrieval and ranking.
Given clinical evidence (diagnoses, procedures), find candidate ICD-10 and CPT codes
and rank by relevance.

Primary source  : NLM Clinical Table Search Service API (free, no key required).
Fallback source : Local CSV databases via the validator singleton.
"""

import logging
import re
from typing import Any, Optional

from coding import api_client
from coding.validation import validator

logger = logging.getLogger(__name__)


class CodeRetriever:
    """
    Retrieve and rank candidate medical codes based on clinical evidence.
    Uses the validator's CSV databases for authoritative code lookup.
    """

    @staticmethod
    def _tokenize_evidence(evidence: str) -> list[str]:
        """Break evidence text into meaningful tokens for matching."""
        # Remove special chars, keep alphanumeric and common medical terms
        text = evidence.lower()
        # Remove parenthetical notes
        text = re.sub(r'\([^)]*\)', ' ', text)
        # Split by non-alphanumeric
        tokens = re.findall(r'[a-z0-9]+', text)
        # Filter out very short tokens
        tokens = [t for t in tokens if len(t) > 2]
        return tokens

    @staticmethod
    def _calculate_relevance_score(
        evidence_tokens: list[str],
        code_tokens: set[str],
        code_description: str,
    ) -> float:
        """
        Calculate relevance between evidence and a candidate code.
        Returns score 0.0 - 1.0
        """
        if not evidence_tokens or not code_tokens:
            return 0.0

        # Exact token matches
        matched_tokens = set(evidence_tokens) & code_tokens
        token_score = len(matched_tokens) / len(set(evidence_tokens))

        # Bonus for key medical terms appearing in description
        description_lower = code_description.lower()
        evidence_phrase = " ".join(evidence_tokens[:10])  # first 10 tokens
        
        phrase_score = 0.0
        if len(evidence_phrase) > 5 and evidence_phrase in description_lower:
            phrase_score = 0.5

        # Weighted combination
        score = (token_score * 0.7) + (phrase_score * 0.3)
        return min(1.0, score)

    @staticmethod
    def retrieve_icd_candidates(
        diagnosis_text: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[dict[str, Any]]:
        """
        Retrieve top ICD-10 candidates for a diagnosis.

        Primary: NLM Clinical Table Search API.
        Fallback: Local CSV token-overlap search.

        Args:
            diagnosis_text: Clinical description of diagnosis
            top_k: Return top N matches
            min_score: Minimum relevance score to include (only used in CSV fallback)

        Returns:
            [{
                "code": "E11.9",
                "description": "Type 2 diabetes...",
                "score": 0.85,
                "source": "nlm_api" | "csv_fallback"
            }, ...]
        """
        if not diagnosis_text:
            return []

        # --- Primary: NLM API ---
        api_results = api_client.search_icd10(diagnosis_text, top_k=top_k)
        if api_results:
            logger.debug(
                "ICD retrieve via NLM API: %d results for '%s'",
                len(api_results), diagnosis_text[:60],
            )
            return [
                {
                    "code": r["code"],
                    "description": r["description"],
                    "score": round(1.0 - (idx * 0.05), 3),  # rank-based pseudo-score
                    "source": "nlm_api",
                }
                for idx, r in enumerate(api_results)
            ]

        # --- Fallback: CSV token search ---
        logger.warning("NLM API unavailable for ICD retrieve — using CSV fallback")
        validator._ensure_csv_loaded()
        if not validator.icd10_db:
            return []

        evidence_tokens = CodeRetriever._tokenize_evidence(diagnosis_text)
        candidates = []
        for code, description in validator.icd10_db.items():
            code_tokens = validator.icd_tokens.get(code, set())
            score = CodeRetriever._calculate_relevance_score(
                evidence_tokens, code_tokens, description
            )
            if score >= min_score:
                candidates.append({
                    "code": code,
                    "description": description,
                    "score": round(score, 3),
                    "source": "csv_fallback",
                })
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]

    @staticmethod
    def retrieve_cpt_candidates(
        procedure_text: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[dict[str, Any]]:
        """
        Retrieve top CPT/HCPCS candidates for a procedure.

        Primary: NLM Clinical Table Search API (HCPCS endpoint, covers CPT Level I).
        Fallback: Local CSV token-overlap search.

        Args:
            procedure_text: Clinical description of procedure
            top_k: Return top N matches
            min_score: Minimum relevance score to include (only used in CSV fallback)

        Returns:
            [{
                "code": "99213",
                "description": "Office visit, established patient...",
                "score": 0.82,
                "source": "nlm_api" | "csv_fallback"
            }, ...]
        """
        if not procedure_text:
            return []

        # --- Primary: NLM API ---
        api_results = api_client.search_cpt(procedure_text, top_k=top_k)
        if api_results:
            logger.debug(
                "CPT retrieve via NLM API: %d results for '%s'",
                len(api_results), procedure_text[:60],
            )
            return [
                {
                    "code": r["code"],
                    "description": r["description"],
                    "score": round(1.0 - (idx * 0.05), 3),
                    "source": "nlm_api",
                }
                for idx, r in enumerate(api_results)
            ]

        # --- Fallback: CSV token search ---
        logger.warning("NLM API unavailable for CPT retrieve — using CSV fallback")
        validator._ensure_csv_loaded()
        if not validator.cpt_db:
            return []

        evidence_tokens = CodeRetriever._tokenize_evidence(procedure_text)
        candidates = []
        for code, description in validator.cpt_db.items():
            code_tokens = validator.cpt_tokens.get(code, set())
            score = CodeRetriever._calculate_relevance_score(
                evidence_tokens, code_tokens, description
            )
            if score >= min_score:
                candidates.append({
                    "code": code,
                    "description": description,
                    "score": round(score, 3),
                    "source": "csv_fallback",
                })
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]

    @staticmethod
    def score_llm_code_against_evidence(
        code_system: str,
        code: str,
        evidence_text: str,
    ) -> float:
        """
        Score how well an LLM-generated code matches the clinical evidence.

        Looks up the code description via NLM API first; falls back to CSV.
        Returns: 0.0 - 1.0 score
        """
        # --- Resolve description: API first ---
        description = ""
        if code_system == "ICD10":
            found, desc = api_client.lookup_icd10(code)
            if found and desc:
                description = desc
            else:
                # Fallback to CSV
                validator._ensure_csv_loaded()
                code_upper = code.replace(".", "").upper()
                description = validator.icd10_db.get(code_upper, "")
        elif code_system == "CPT":
            found, desc = api_client.lookup_cpt(code)
            if found and desc:
                description = desc
            else:
                validator._ensure_csv_loaded()
                description = validator.cpt_db.get(code.upper(), "")
        else:
            return 0.0

        if not description:
            return 0.0

        code_tokens = CodeRetriever._tokenize_evidence(description)
        evidence_tokens = CodeRetriever._tokenize_evidence(evidence_text)

        return CodeRetriever._calculate_relevance_score(
            list(evidence_tokens),
            set(code_tokens),
            description,
        )

    @staticmethod
    def _semantic_validation(
        code: dict[str, Any],
        description: str,
    ) -> tuple[bool, str]:
        """
        Perform semantic validation checks for systematic coding errors.
        Returns (is_valid, reason_if_invalid)
        """
        code_val = code.get("code", "")
        evidence_text = code.get("evidence_text", "").lower()
        system = code.get("system", "")

        # Check S80 vs S81 (injury vs open wound)
        if code_val.startswith("S8") and description and system == "ICD10":
            # S81.xxx = open wound (laceration/puncture)
            # S80.xxx = contusion/injury (swelling, bruising, pain)
            is_open_wound = "81" in code_val
            has_open_wound_evidence = any(
                word in evidence_text for word in 
                ["laceration", "cut", "tear", "bleeding", "puncture", "wound"]
            )
            has_injury_evidence = any(
                word in evidence_text for word in 
                ["swelling", "pain", "bruise", "contusion", "edema"]
            )

            # If code is S81 (open wound) but evidence only mentions swelling/pain
            if is_open_wound and has_injury_evidence and not has_open_wound_evidence:
                return False, f"Code {code_val} is open wound (S81) but evidence '{evidence_text}' describes injury/swelling (should be S80)"

        # Check 7th character A vs D for historical injuries
        if code_val.endswith("A") and system == "ICD10":
            has_historical_keywords = any(
                word in evidence_text for word in 
                ["history", "previous", "prior", "past", "old", "from June", "from November", "from May"]
            )
            if has_historical_keywords:
                return False, f"Code {code_val} uses 'A' (initial) but evidence '{evidence_text}' indicates historical/previous injury (should use 'D' for subsequent)"

        # Check V23.4XXA vs V23.9XXA (specific vehicle vs unspecified)
        if code_val.startswith("V23.4"):
            has_car_evidence = "car" in evidence_text
            has_truck_van_evidence = any(word in evidence_text for word in ["truck", "van", "pickup"])
            # V23.4 specifically = truck/van. If evidence says "car", should be V23.9
            if has_car_evidence and not has_truck_van_evidence:
                return False, f"Code {code_val} is motorcycle-truck/van collision but evidence '{evidence_text}' says car (should be V23.9XXA)"

        # Check Y92 place codes (Y92.830 park vs Y92.410 street)
        if code_val.startswith("Y92"):
            is_park_code = code_val == "Y92.830"
            is_road_code = code_val in ["Y92.410", "Y92.411"]
            
            has_road_evidence = any(word in evidence_text for word in 
                ["road", "highway", "street", "roadway", "interstate"])
            has_park_evidence = "park" in evidence_text

            if is_park_code and has_road_evidence:
                return False, f"Code {code_val} is public park but evidence '{evidence_text}' indicates road/highway (should be Y92.410/Y92.411)"
            
            if is_road_code and has_park_evidence:
                return False, f"Code {code_val} is street/highway but evidence '{evidence_text}' indicates park (should be Y92.830)"

        # Check CPT wound codes - size dependent
        if system == "CPT" and code_val in ["12001", "12002", "12004"]:
            has_size_info = any(word in evidence_text for word in 
                ["cm", "centimeter", "2.5", "7.5", "small", "large", "size"])
            if not has_size_info:
                # Don't fail, but reduce confidence
                code["confidence"] = min(code.get("confidence", 0.7), 0.60)
                return True, f"Code {code_val} (CPT wound repair) lacks explicit size specification"

        return True, ""

    @staticmethod
    def is_codeable_by_source(source_info: dict[str, Any]) -> tuple[bool, str]:
        """
        Check if a diagnosis is codeable based on source validation (ICD-10-CM Section I.B.1).
        
        Rule: Code only physician-confirmed diagnoses. Never code patient-only statements.
        
        Args:
            source_info: dict with keys:
                - source: "physician_confirmed", "patient_reported", "historical", "unconfirmed_suspected"
                - is_current_visit: bool - True if being treated/managed today
                - affected_current_care: bool - True if historical condition affects current treatment decision
                - source_evidence: str - text supporting the source classification
        
        Returns:
            (is_codeable: bool, reason: str)
        """
        source = source_info.get("source", "")
        is_current = source_info.get("is_current_visit", False)
        affects_care = source_info.get("affects_current_care", False)
        evidence = source_info.get("source_evidence", "")
        
        # GATE 1: Reject patient-only statements
        if source == "patient_reported":
            return False, f"Source: patient_reported | Evidence: {evidence} | Decision: REJECT | Reason: Patient statement without physician confirmation (ICD-10-CM I.B.1)"
        
        # GATE 2: Reject unconfirmed suspected diagnoses
        if source == "unconfirmed_suspected":
            return False, f"Source: unconfirmed_suspected | Evidence: {evidence} | Decision: REJECT | Reason: Unconfirmed suspected diagnosis (doctor said possible/probable/rule out)"
        
        # GATE 3: Accept physician-confirmed diagnoses at current visit
        if source == "physician_confirmed" and is_current:
            return True, f"Source: physician_confirmed | Current visit: true | Decision: APPROVE | Reason: Physician confirmed and actively treated at this visit"
        
        # GATE 4: Historical diagnoses only coded if affecting current care (use Z87.x)
        if source == "historical":
            if affects_care:
                return True, f"Source: historical | Affects current care: true | Decision: APPROVE WITH Z87.x | Reason: Historical condition documented as affecting current treatment decisions"
            else:
                return False, f"Source: historical | Affects current care: false | Decision: REJECT | Reason: Historical condition not actively relevant to current visit"
        
        # GATE 5: Default behavior for unknown source
        if not source or source == "physician_confirmed":
            return True, f"Source: {source} | Decision: APPROVE | Reason: Treating as physician-confirmed by default"
        
        return False, f"Source: {source} | Decision: REJECT | Reason: Source type not recognized"

    @staticmethod
    def flag_codes_for_review(
        codes: list[dict[str, Any]],
        evidence: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """
        Analyze generated codes and flag ones that may need review.

        Returns:
            (updated_codes, flag_reasons)
        """
        flagged_codes = []
        flag_reasons = []

        for code in codes:
            system = code.get("system")
            code_val = code.get("code", "")
            evidence_text = code.get("evidence_text", "")
            confidence = code.get("confidence", 0.5)
            description = code.get("description", "")

            # Flag if confidence is very low
            if confidence < 0.6:
                flag_reasons.append(
                    f"Code {code_val} has low confidence ({confidence:.2f})"
                )
                code["needs_review"] = True

            # Flag if no supporting evidence
            if not evidence_text:
                flag_reasons.append(
                    f"Code {code_val} lacks supporting evidence text"
                )
                code["needs_review"] = True

            # Semantic validation for systematic errors
            is_semantically_valid, validation_reason = CodeRetriever._semantic_validation(code, description)
            if not is_semantically_valid and validation_reason:
                flag_reasons.append(validation_reason)
                code["needs_review"] = True

            # Flag ONLY if evidence-confidence mismatch is SEVERE and REAL
            # Skip token-based flagging for high-confidence codes with evidence present
            # (token-based matching is too imperfect for medical terms)
            if evidence_text and confidence < 0.85:
                # Only check token matching for lower-confidence codes
                score_vs_evidence = CodeRetriever.score_llm_code_against_evidence(
                    system,
                    code_val,
                    evidence_text,
                )
                # Flag ONLY if score is near zero AND confidence is low
                if score_vs_evidence < 0.05 and confidence < 0.75:
                    flag_reasons.append(
                        f"Code {code_val} confidence ({confidence:.2f}) but "
                        f"evidence match is very weak ({score_vs_evidence:.2f})"
                    )
                    code["needs_review"] = True

        return codes, flag_reasons
