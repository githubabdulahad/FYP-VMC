"""
coding/diagnosis_mapper.py

Maps clinical diagnoses to ICD-10/CPT codes with full specificity.
Handles trauma S codes, condition E codes, etc. systematically.

This is Layer 3 of the reliable diagnosis pipeline.
"""

import re
from typing import Any, Optional
from coding.validation import validator


class DiagnosisToCodeMapper:
    """
    Systematically map clinical diagnoses to ICD-10 and CPT codes.
    Ensures specificity (laterality, site, severity) is captured.
    """

    # TRAUMA INJURY ICD-10 CODE PATTERNS
    # S-codes: Injuries, poisoning, consequences of external causes
    TRAUMA_CODE_MAPPING = {
        # Arm/Forearm lacerations/wounds (S51.X)
        ("laceration", "arm", "right"): ["S51.811A", "S51.811"],  # Open wound right forearm
        ("laceration", "arm", "left"): ["S51.811A", "S51.811"],
        ("laceration", "arm", None): ["S51.9A", "S51.9"],
        ("cut", "arm", "right"): ["S51.811A"],
        ("cut", "arm", "left"): ["S51.811A"],

        # Leg/Thigh injuries (S70-S79)
        ("fracture", "leg", "left"): ["S72.911A", "S72.911"],  # Fracture left femur
        ("fracture", "leg", "right"): ["S72.901A", "S72.901"],
        ("contusion", "leg", "left"): ["S80.011A"],  # Contusion left knee
        ("swelling", "leg", "left"): ["S80.011A"],  # Often indicates contusion/edema

        # Neck/Whiplash (S10-S19)
        ("whiplash", "neck", None): ["S13.4A"],  # Sprain of cervical spine
        ("neck strain", "neck", None): ["S16.1A"],  # Strain of neck muscle

        # Head/Face trauma (S00-S09)
        ("fracture", "head", None): ["S02.91A"],
        ("laceration", "head", None): ["S01.90A"],
    }

    # CONDITION CODE PATTERNS (E, I, J, K codes, etc.)
    CONDITION_CODE_MAPPING = {
        "type 2 diabetes": ["E11.9"],
        "diabetes": ["E11.9"],
        "hypertension": ["I10"],
        "high blood pressure": ["I10"],
        "asthma": ["J45.9"],
        "copd": ["J44.9"],
        "heart failure": ["I50.9"],
        "venous insufficiency": ["I87.2"],
        "arthritis": ["M19.90"],
    }

    # EXTERNAL CAUSE CODES (V, W, X, Y codes) — what caused the trauma
    EXTERNAL_CAUSE_MAPPING = {
        "motorcycle collision": ["V28.5XXA"],  # Motorcycle rider in collision with car
        "motor vehicle accident": ["V89.2XXA"],
        "car accident": ["V89.2XXA"],
        "fall": ["W00-W19"],
        "workplace": ["Y92.6"],  # Workplace as place of occurrence
    }

    @staticmethod
    def _find_best_code(
        description: str,
        location: Optional[str],
        laterality: Optional[str],
        severity: Optional[str],
        code_mapping: dict,
    ) -> Optional[str]:
        """
        Find best matching code from mapping, considering specificity.

        Priority:
        1. Exact match: description + location + laterality
        2. Description + location (ignore laterality)
        3. Description only
        """
        desc_lower = description.lower()

        # Try most specific match first
        if location and laterality:
            key = (desc_lower, location, laterality)
            if key in code_mapping:
                return code_mapping[key][0]

        # Try with location, ignore laterality
        if location:
            key = (desc_lower, location, None)
            if key in code_mapping:
                return code_mapping[key][0]

        # Try description only
        for mapped_desc, codes in code_mapping.items():
            if isinstance(mapped_desc, tuple):
                if desc_lower in mapped_desc[0]:
                    return codes[0]
            else:
                if desc_lower in mapped_desc:
                    return codes[0]

        return None

    @staticmethod
    def map_trauma_to_icd(
        diagnosis_name: str,
        location: Optional[str],
        laterality: Optional[str],
        severity: Optional[str],
    ) -> dict[str, Any]:
        """
        Map trauma/injury diagnosis to ICD-10 code with specificity.

        Args:
            diagnosis_name: e.g., "Laceration, right arm"
            location: e.g., "arm", "leg"
            laterality: e.g., "left", "right", "bilateral"
            severity: e.g., "mild", "severe"

        Returns:
            {
                "code": "S51.811A",
                "description": "Open wound of right forearm, initial encounter",
                "confidence": 0.9,
                "specificity": "high"  # or "medium" or "low"
            }
        """
        # Search trauma mapping
        code = DiagnosisToCodeMapper._find_best_code(
            diagnosis_name,
            location,
            laterality,
            severity,
            DiagnosisToCodeMapper.TRAUMA_CODE_MAPPING,
        )

        if code:
            # Get full description from validator
            code_clean = code.replace(".", "").upper()
            db_desc = validator.icd10_db.get(code_clean, "")

            # Determine specificity
            specificity = "high" if laterality else "medium"

            return {
                "code": code,
                "description": db_desc or diagnosis_name,
                "confidence": 0.85 if laterality else 0.75,
                "specificity": specificity,
            }

        return {
            "code": None,
            "description": diagnosis_name,
            "confidence": 0.5,
            "specificity": "low",
        }

    @staticmethod
    def map_condition_to_icd(condition_name: str) -> dict[str, Any]:
        """
        Map clinical condition to ICD-10 code.

        Args:
            condition_name: e.g., "Type 2 Diabetes", "Hypertension"

        Returns:
            {
                "code": "E11.9",
                "description": "Type 2 diabetes mellitus without complications",
                "confidence": 0.9,
                "specificity": "medium"
            }
        """
        condition_lower = condition_name.lower()

        # Try exact match
        for mapped_cond, codes in DiagnosisToCodeMapper.CONDITION_CODE_MAPPING.items():
            if mapped_cond in condition_lower:
                code = codes[0]
                code_clean = code.replace(".", "").upper()
                db_desc = validator.icd10_db.get(code_clean, "")

                return {
                    "code": code,
                    "description": db_desc or condition_name,
                    "confidence": 0.9,
                    "specificity": "medium",
                }

        # No match found - try retrieval
        from coding.code_retrieval import CodeRetriever
        candidates = CodeRetriever.retrieve_icd_candidates(condition_name, top_k=1, min_score=0.3)

        if candidates:
            return {
                "code": candidates[0]["code"],
                "description": candidates[0]["description"],
                "confidence": candidates[0]["score"],
                "specificity": "low",
            }

        return {
            "code": None,
            "description": condition_name,
            "confidence": 0.3,
            "specificity": "low",
        }

    @staticmethod
    def map_external_cause_to_icd(cause_description: str) -> Optional[str]:
        """
        Map mechanism of injury to external cause code (V/W/X/Y codes).

        Args:
            cause_description: e.g., "Motorcycle collision with car"

        Returns:
            ICD-10 code or None
        """
        cause_lower = cause_description.lower()

        for mapped_cause, codes in DiagnosisToCodeMapper.EXTERNAL_CAUSE_MAPPING.items():
            if mapped_cause in cause_lower:
                return codes[0]

        return None

    @staticmethod
    def map_diagnosis_to_codes(
        diagnosis: "ExtractedDiagnosis",  # From diagnosis_parser
    ) -> dict[str, Any]:
        """
        Map a complete extracted diagnosis to ICD-10 codes.

        Returns:
            {
                "primary_code": {...},
                "external_cause_code": {...},
                "specificity_score": 0.85,
                "mapping_confidence": 0.9,
            }
        """
        from coding.diagnosis_parser import DiagnosisType

        primary_code = None
        external_cause = None

        if diagnosis.diagnosis_type == DiagnosisType.TRAUMA_INJURY:
            primary_code = DiagnosisToCodeMapper.map_trauma_to_icd(
                diagnosis.diagnosis_name,
                diagnosis.primary_location,
                diagnosis.laterality,
                diagnosis.severity,
            )

            # Add external cause if trauma
            if diagnosis.source_text:
                external_cause = DiagnosisToCodeMapper.map_external_cause_to_icd(diagnosis.source_text)

        elif diagnosis.diagnosis_type == DiagnosisType.CHRONIC_CONDITION:
            primary_code = DiagnosisToCodeMapper.map_condition_to_icd(diagnosis.diagnosis_name)

        # Calculate overall specificity
        specificity_factors = []
        if diagnosis.primary_location:
            specificity_factors.append(0.3)
        if diagnosis.laterality:
            specificity_factors.append(0.3)
        if diagnosis.severity:
            specificity_factors.append(0.2)
        if diagnosis.acuity:
            specificity_factors.append(0.2)

        specificity_score = sum(specificity_factors) if specificity_factors else 0.3

        return {
            "primary_code": primary_code,
            "external_cause_code": external_cause,
            "specificity_score": min(1.0, specificity_score),
            "mapping_confidence": diagnosis.confidence,
            "diagnosis_name": diagnosis.diagnosis_name,
        }
