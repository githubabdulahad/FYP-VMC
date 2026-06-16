"""
coding/diagnosis_parser.py

Robust clinical narrative parser that extracts diagnoses independently of SOAP structure.
Handles trauma, chronic disease, acute conditions, and mixed narratives.

This is Layer 1 & 2 of the reliable diagnosis pipeline.
"""

import re
from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum


class DiagnosisType(Enum):
    TRAUMA_INJURY = "trauma_injury"
    CHRONIC_CONDITION = "chronic_condition"
    ACUTE_CONDITION = "acute_condition"
    INFECTIOUS = "infectious"
    METABOLIC = "metabolic"
    PROCEDURE_INDICATION = "procedure_indication"
    COMPLICATION = "complication"


@dataclass
class ClinicalFinding:
    """Raw clinical finding extracted from narrative."""
    finding_type: str  # injury, condition, symptom, vital, procedure
    location: Optional[str] = None  # body part: arm, leg, chest, etc.
    laterality: Optional[str] = None  # left, right, bilateral
    severity: Optional[str] = None  # mild, moderate, severe, critical
    description: str = ""
    context: str = ""  # surrounding text for disambiguation
    confidence: float = 0.8
    raw_text: str = ""  # exact text from source


@dataclass
class ExtractedDiagnosis:
    """Structured diagnosis extracted from clinical narrative."""
    diagnosis_name: str
    diagnosis_type: DiagnosisType
    primary_location: Optional[str] = None
    laterality: Optional[str] = None
    severity: Optional[str] = None
    acuity: Optional[str] = None
    icd_category: Optional[str] = None  # S (trauma), E (metabolic), etc.
    related_findings: list[ClinicalFinding] = None
    confidence: float = 0.8
    source_text: str = ""

    def __post_init__(self):
        if self.related_findings is None:
            self.related_findings = []


class ClinicalNarrativeParser:
    """
    Parse unstructured clinical narratives to extract diagnoses.
    Works independently of SOAP structure - processes raw clinical text.
    """

    # TRAUMA/INJURY PATTERNS
    TRAUMA_KEYWORDS = {
        "injury": ["injury", "injured", "trauma", "hurt", "wound", "laceration", "cut", "fracture"],
        "motor_vehicle": ["accident", "collision", "hit", "struck", "motor", "motorcycle", "car", "vehicle"],
        "fall": ["fell", "fall", "tripped", "dropped", "slipped"],
        "mechanism": ["accident", "trauma", "incident", "mechanism"],
    }

    BODY_PART_KEYWORDS = {
        "arm": ["arm", "upper extremity", "shoulder", "elbow", "wrist", "hand", "forearm", "upper arm"],
        "leg": ["leg", "lower extremity", "knee", "ankle", "hip", "thigh", "calf"],
        "torso": ["chest", "trunk", "abdomen", "back", "ribcage", "spine"],
        "head": ["head", "face", "skull", "brain", "eye", "nose"],
        "neck": ["neck", "cervical", "nape"],
    }

    WOUND_TYPE_KEYWORDS = {
        "laceration": ["cut", "laceration", "lacerations", "gash"],
        "fracture": ["fracture", "fractured", "broken", "break"],
        "contusion": ["bruise", "bruised", "contusion", "swelling", "edema"],
        "wound": ["wound", "wounds", "open"],
        "strain": ["strain", "sprain", "tear"],
    }

    SEVERITY_KEYWORDS = {
        "mild": ["mild", "minimal", "slight", "minor"],
        "moderate": ["moderate"],
        "severe": ["severe", "serious", "major", "significant"],
        "critical": ["critical", "life-threatening"],
    }

    # CHRONIC CONDITION PATTERNS
    CHRONIC_KEYWORDS = [
        "chronic", "long-standing", "ongoing", "persistent", "recurrent", "diabetes",
        "hypertension", "heart disease", "asthma", "copd", "arthritis", "fibromyalgia"
    ]

    # ACUTE CONDITION PATTERNS
    ACUTE_KEYWORDS = ["acute", "sudden", "new onset", "recently", "just", "started"]

    @staticmethod
    def _extract_body_part(text: str) -> Optional[tuple[str, Optional[str]]]:
        """Extract body part and laterality from text."""
        text_lower = text.lower()

        # Check for laterality
        laterality = None
        if re.search(r'\bleft\b|\blt\b', text_lower):
            laterality = "left"
        elif re.search(r'\bright\b|\brt\b', text_lower):
            laterality = "right"
        elif re.search(r'\bbilateral\b|\bboth\b', text_lower):
            laterality = "bilateral"

        # Find body part
        for part_type, keywords in ClinicalNarrativeParser.BODY_PART_KEYWORDS.items():
            for kw in keywords:
                if re.search(r'\b' + kw + r'\b', text_lower):
                    return part_type, laterality

        return None, laterality

    @staticmethod
    def _extract_severity(text: str) -> Optional[str]:
        """Extract severity from text."""
        text_lower = text.lower()
        for severity, keywords in ClinicalNarrativeParser.SEVERITY_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return severity
        return None

    @staticmethod
    def _detect_trauma(text: str) -> Optional[ClinicalFinding]:
        """Detect trauma/injury in text."""
        text_lower = text.lower()

        # Look for trauma indicators
        trauma_found = False
        for category, keywords in ClinicalNarrativeParser.TRAUMA_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                trauma_found = True
                break

        if not trauma_found:
            return None

        # Extract wound type
        wound_type = "unspecified injury"
        for wtype, keywords in ClinicalNarrativeParser.WOUND_TYPE_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                wound_type = wtype
                break

        # Extract body part
        body_part, laterality = ClinicalNarrativeParser._extract_body_part(text)

        # Extract severity
        severity = ClinicalNarrativeParser._extract_severity(text)

        return ClinicalFinding(
            finding_type="injury",
            location=body_part,
            laterality=laterality,
            severity=severity,
            description=wound_type,
            context=text,
            raw_text=text,
        )

    @staticmethod
    def _detect_conditions(text: str) -> list[ClinicalFinding]:
        """Detect chronic/acute conditions in text."""
        findings = []
        text_lower = text.lower()

        # Split into sentences
        sentences = re.split(r'[.!?]', text)

        for sentence in sentences:
            sentence_lower = sentence.lower()

            # Chronic conditions
            if any(kw in sentence_lower for kw in ClinicalNarrativeParser.CHRONIC_KEYWORDS):
                # Extract what condition
                for kw in ClinicalNarrativeParser.CHRONIC_KEYWORDS:
                    if kw in sentence_lower:
                        findings.append(ClinicalFinding(
                            finding_type="condition",
                            description=kw,
                            context=sentence,
                            raw_text=sentence,
                        ))
                        break

            # Acute conditions
            if any(kw in sentence_lower for kw in ClinicalNarrativeParser.ACUTE_KEYWORDS):
                # Look for condition mentioned
                if "pain" in sentence_lower or "swelling" in sentence_lower or "fever" in sentence_lower:
                    findings.append(ClinicalFinding(
                        finding_type="symptom",
                        description=sentence.strip(),
                        context=sentence,
                        raw_text=sentence,
                    ))

        return findings

    @staticmethod
    def _detect_procedures(text: str) -> list[ClinicalFinding]:
        """Detect procedures mentioned in text."""
        findings = []
        text_lower = text.lower()

        procedure_keywords = [
            "imaging", "x-ray", "ct", "mri", "scan", "ultrasound", "echocardiogram",
            "wound cleaning", "dressing", "surgery", "repair", "suture", "injection",
            "physiotherapy", "physical therapy", "observation", "monitoring",
        ]

        for proc in procedure_keywords:
            if proc in text_lower:
                findings.append(ClinicalFinding(
                    finding_type="procedure",
                    description=proc,
                    context=text,
                    raw_text=text,
                ))

        return findings

    @staticmethod
    def parse_clinical_narrative(raw_text: str) -> list[ExtractedDiagnosis]:
        """
        Parse raw clinical narrative and extract structured diagnoses.

        Args:
            raw_text: Unstructured clinical narrative (conversation, notes, etc.)

        Returns:
            List of structured diagnoses with metadata
        """
        diagnoses = []

        # Extract trauma/injuries
        lines = raw_text.split('\n')
        for line in lines:
            if len(line) > 10:
                trauma = ClinicalNarrativeParser._detect_trauma(line)
                if trauma:
                    # Convert finding to diagnosis
                    dx_name = f"{trauma.severity or ''} {trauma.description}".strip()
                    if trauma.location:
                        dx_name += f" ({trauma.location})"
                    if trauma.laterality:
                        dx_name += f", {trauma.laterality} side"

                    diagnoses.append(ExtractedDiagnosis(
                        diagnosis_name=dx_name,
                        diagnosis_type=DiagnosisType.TRAUMA_INJURY,
                        primary_location=trauma.location,
                        laterality=trauma.laterality,
                        severity=trauma.severity,
                        icd_category="S",  # S codes are trauma
                        related_findings=[trauma],
                        confidence=0.85,
                        source_text=line,
                    ))

        # Extract conditions
        conditions = ClinicalNarrativeParser._detect_conditions(raw_text)
        for cond in conditions:
            diagnoses.append(ExtractedDiagnosis(
                diagnosis_name=cond.description,
                diagnosis_type=DiagnosisType.CHRONIC_CONDITION if "chronic" in raw_text.lower() else DiagnosisType.ACUTE_CONDITION,
                related_findings=[cond],
                confidence=0.75,
                source_text=cond.context,
            ))

        return diagnoses


# Example usage
if __name__ == "__main__":
    text = """
    Doctor: What injuries did you sustain?
    Patient: My left leg took most of the impact — it's swollen and painful. 
    I also have deep cuts on my right arm.
    """

    diagnoses = ClinicalNarrativeParser.parse_clinical_narrative(text)
    for dx in diagnoses:
        print(f"✓ {dx.diagnosis_name}")
        print(f"  Type: {dx.diagnosis_type.value}")
        print(f"  Location: {dx.primary_location}, Laterality: {dx.laterality}")
        print(f"  Confidence: {dx.confidence}")
        print()
