"""
coding/evidence_extractor.py

Extract structured clinical evidence from SOAP notes and raw text.
Identifies diagnoses, procedures, findings, symptoms with metadata (acuity, laterality, etc.)
"""

import re
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class Diagnosis:
    """Extracted diagnosis with clinical modifiers AND SOURCE ATTRIBUTION."""
    condition: str
    acuity: Optional[str] = None  # acute, chronic, acute-on-chronic
    laterality: Optional[str] = None  # left, right, bilateral
    complications: list[str] = None
    stage: Optional[str] = None
    severity: Optional[str] = None
    
    # SOURCE VALIDATION FIELDS (NEW - ICD-10-CM Section I.B.1 compliance)
    source: Optional[str] = None  # "physician_confirmed", "patient_reported", "historical"
    source_evidence: Optional[str] = None  # The exact text that attributes this diagnosis
    is_current_visit: Optional[bool] = None  # True if being managed today; False if historical
    confidence_in_source: Optional[float] = None  # 0.0-1.0: confidence in source classification

    def __post_init__(self):
        if self.complications is None:
            self.complications = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "acuity": self.acuity,
            "laterality": self.laterality,
            "complications": self.complications,
            "stage": self.stage,
            "severity": self.severity,
            "source": self.source,
            "source_evidence": self.source_evidence,
            "is_current_visit": self.is_current_visit,
            "confidence_in_source": self.confidence_in_source,
        }


@dataclass
class Procedure:
    """Extracted procedure with technical details."""
    name: str
    approach: Optional[str] = None  # open, laparoscopic, endoscopic, percutaneous, imaging
    site: Optional[str] = None  # anatomical location
    laterality: Optional[str] = None
    urgency: Optional[str] = None  # emergency, elective, urgent

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "approach": self.approach,
            "site": self.site,
            "laterality": self.laterality,
            "urgency": self.urgency,
        }


class EvidenceExtractor:
    """Extract structured clinical evidence from SOAP notes."""

    # Acuity keywords
    ACUITY_KEYWORDS = {
        "acute": ["acute", "sudden", "newly", "new onset"],
        "chronic": ["chronic", "long-standing", "longstanding", "ongoing", "persistent"],
        "acute-on-chronic": ["acute on chronic", "acute exacerbation"],
    }

    # Severity keywords
    SEVERITY_KEYWORDS = {
        "mild": ["mild", "minimal", "slight", "minimal"],
        "moderate": ["moderate"],
        "severe": ["severe", "significant", "marked"],
        "critical": ["critical", "life-threatening"],
    }

    # Laterality keywords
    LATERALITY_KEYWORDS = {
        "left": ["left", "lt", "l side"],
        "right": ["right", "rt", "r side"],
        "bilateral": ["bilateral", "both sides", "both"],
    }

    # Common complications
    COMPLICATION_KEYWORDS = [
        "abscess", "perforation", "peritonitis", "gangrene", "hemorrhage",
        "infection", "sepsis", "necrosis", "rupture", "obstruction",
        "fistula", "stenosis", "adhesion", "scarring", "bleeding",
    ]

    # Procedure approach keywords
    APPROACH_KEYWORDS = {
        "open": ["open", "surgical incision"],
        "laparoscopic": ["laparoscopic", "lap", "minimally invasive"],
        "endoscopic": ["endoscopic", "endo", "ERCP", "EGD", "colonoscopy"],
        "percutaneous": ["percutaneous", "needle", "catheter", "drainage", "biopsy"],
        "imaging": ["imaging", "ct", "mri", "ultrasound", "x-ray", "chest x-ray", "echocardiogram"],
        "topical": ["topical", "cream", "ointment"],
        "injection": ["injection", "iv", "intravenous", "intramuscular", "im"],
    }

    # TRAUMA-SPECIFIC KEYWORDS
    # Body parts
    BODY_PARTS = {
        "leg": ["leg", "thigh", "calf", "shin", "ankle", "foot"],
        "arm": ["arm", "forearm", "hand", "wrist", "elbow", "upper arm"],
        "head": ["head", "skull", "scalp", "face", "forehead"],
        "neck": ["neck", "cervical", "c-spine"],
        "back": ["back", "spine", "lumbar", "thoracic", "vertebra"],
        "chest": ["chest", "rib", "thorax", "sternum"],
        "abdomen": ["abdomen", "belly", "gut", "viscera"],
        "pelvis": ["pelvis", "hip", "pelvic"],
    }

    # Wound/injury types
    INJURY_TYPES = {
        "laceration": ["cut", "cuts", "laceration", "lacerations", "gash", "gashes"],
        "contusion": ["bruise", "bruising", "contusion", "contusions", "bump"],
        "abrasion": ["abrasion", "scrape", "scrapes", "road rash"],
        "fracture": ["fracture", "break", "broken", "fractures"],
        "strain": ["strain", "strains", "sprain", "sprains"],
        "swelling": ["swelling", "edema", "swollen", "puffed", "puffy"],
        "hematoma": ["hematoma", "hematomas", "bruise", "collection"],
        "whiplash": ["whiplash", "whip injury"],
        "crush": ["crush", "crushed", "compression"],
        "burn": ["burn", "burns", "burned", "scald"],
    }

    # Trauma mechanisms
    TRAUMA_KEYWORDS = [
        "accident", "collision", "hit", "struck", "impact", "fell", "fall", "falling",
        "motorcycle", "car", "vehicle", "crash", "trauma", "traumatic", "injury", "injuries",
        "rear-end", "struck", "pulling out", "knocked", "injured", "hurt", "wound", "wounds",
    ]

    @staticmethod
    def _extract_modifiers(text: str) -> dict[str, Optional[str]]:
        """Extract acuity, severity, laterality from text."""
        text_lower = text.lower()
        modifiers = {
            "acuity": None,
            "severity": None,
            "laterality": None,
            "complications": [],
        }

        # Check acuity
        for acuity, keywords in EvidenceExtractor.ACUITY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                modifiers["acuity"] = acuity
                break

        # Check severity
        for severity, keywords in EvidenceExtractor.SEVERITY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                modifiers["severity"] = severity
                break

        # Check laterality
        for laterality, keywords in EvidenceExtractor.LATERALITY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                modifiers["laterality"] = laterality
                break

        # Check complications
        for comp in EvidenceExtractor.COMPLICATION_KEYWORDS:
            if comp in text_lower:
                modifiers["complications"].append(comp)

        return modifiers

    @staticmethod
    def extract_diagnoses(assessment: str) -> list[Diagnosis]:
        """Extract diagnoses from SOAP assessment section using sentence boundaries."""
        if not assessment or not isinstance(assessment, str):
            return []

        diagnoses = []
        
        # Split on sentence boundaries (periods) FIRST, then on numbered lists (1., 2., etc.)
        # This preserves multi-clause diagnoses like "Chronic kidney disease, stage 3a — stable"
        sentences = re.split(r'\.\s+|\n(?=\d\.\s)', assessment)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 3:
                continue
            
            # Clean up meta-tags like [Initial visit], [Established patient]
            cleaned = re.sub(r'\s*\[[^\]]+\]\s*$', '', sentence)
            cleaned = cleaned.strip()
            
            if not cleaned or len(cleaned) < 3:
                continue
            
            # Extract modifiers (acuity, severity, laterality)
            modifiers = EvidenceExtractor._extract_modifiers(cleaned)
            
            # Try to extract stage information (e.g., "stage 3a", "Stage 3a CKD")
            stage_match = re.search(r'stage\s+([0-9]+[a-b]?)', cleaned, re.IGNORECASE)
            stage = stage_match.group(1) if stage_match else None
            
            diagnosis = Diagnosis(
                condition=cleaned.split('\n')[0].strip(),
                acuity=modifiers.get("acuity"),
                severity=modifiers.get("severity"),
                laterality=modifiers.get("laterality"),
                complications=modifiers.get("complications", []),
                stage=stage,
            )
            diagnoses.append(diagnosis)

        return diagnoses

    @staticmethod
    def extract_procedures(plan: str) -> list[Procedure]:
        """Extract procedures from SOAP plan section using sentence boundaries."""
        if not plan or not isinstance(plan, str):
            return []

        procedures = []
        
        # Split on sentence boundaries (periods, newlines) FIRST
        # This prevents "avoid NSAIDs. Initiate tamsulosin..." from being merged
        sentences = re.split(r'\.\s+|\n+', plan)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 3:
                continue
            
            # Skip directives like "avoid NSAIDs", "continue", "counseled"
            # These are treatment instructions, not procedures
            if re.match(r'^(avoid|continue|counseled|discussed|explained)\s+', sentence, re.IGNORECASE):
                continue
            
            # Detect procedure approach
            approach = None
            for ap, keywords in EvidenceExtractor.APPROACH_KEYWORDS.items():
                if any(kw in sentence.lower() for kw in keywords):
                    approach = ap
                    break
            
            modifiers = EvidenceExtractor._extract_modifiers(sentence)
            procedure = Procedure(
                name=sentence.split('\n')[0].strip(),
                approach=approach,
                laterality=modifiers.get("laterality"),
                urgency=None,
            )
            procedures.append(procedure)

        return procedures

    @staticmethod
    def extract_symptoms(subjective: str) -> list[str]:
        """Extract reported symptoms from subjective section."""
        if not subjective or not isinstance(subjective, str):
            return []

        # Comprehensive symptom keywords covering multiple body systems
        symptom_keywords = [
            # Pain and discomfort
            "pain", "ache", "sore", "tender", "discomfort", "cramping",
            # Fever and infection signs
            "fever", "chills", "sweating", "diaphoresis",
            # Constitutional symptoms
            "fatigue", "weakness", "malaise", "lethargy", "tiredness",
            # GI symptoms
            "nausea", "vomiting", "diarrhea", "constipation", "bloating", "loss of appetite", "anorexia",
            # Bleeding/bruising
            "bleeding", "bruising", "hemorrhage", "hematuria",
            # Respiratory symptoms
            "shortness of breath", "dyspnea", "cough", "wheeze", "wheezing",
            "chest pain", "chest discomfort", "palpitations", "tachycardia",
            # Neurological symptoms
            "headache", "dizziness", "vertigo", "syncope", "confusion",
            # Skin symptoms
            "rash", "itching", "pruritus", "hives", "erythema",
            # Sensory symptoms
            "numbness", "tingling", "paresthesia", "neuropathy",
            # Musculoskeletal symptoms
            "swelling", "edema", "stiffness", "joint pain", "arthralgia",
            # Urinary symptoms (critical for BPH/CKD)
            "urinary frequency", "frequency", "urinary retention", "dysuria",
            "nocturia", "polydipsia", "polyuria", "hematuria",
            # Weight and metabolism
            "weight loss", "weight gain", "weight change",
            # Sleep and mood
            "insomnia", "sleep disturbance", "anxiety", "depression",
            # Fluid balance
            "ankle edema", "peripheral edema", "edema", "leg swelling",
            # Temperature and vitals
            "hypothermia", "hyperthermia",
        ]

        symptoms = []
        text_lower = subjective.lower()

        for symptom in symptom_keywords:
            if symptom in text_lower:
                symptoms.append(symptom)

        return list(set(symptoms))  # deduplicate

    @staticmethod
    def extract_findings(objective: str) -> list[dict[str, Any]]:
        """Extract vitals and findings from objective section."""
        if not objective or not isinstance(objective, str):
            return []

        findings = []

        # Extract vital signs with regex patterns
        vital_patterns = {
            "BP": r"(?:BP|blood pressure)[:\s]*(\d+/\d+|\d+\s*over\s*\d+)",
            "HR": r"(?:HR|heart rate|pulse)[:\s]*(\d+)",
            "RR": r"(?:RR|respiratory rate)[:\s]*(\d+)",
            "Temp": r"(?:Temp|temperature)[:\s]*(\d+\.?\d*)",
            "SpO2": r"(?:SpO2|O2 sat|oxygen)[:\s]*(\d+%?)",
            "BMI": r"(?:BMI)[:\s]*(\d+\.?\d*)",
            "Weight": r"(?:weight|wt)[:\s]*(\d+\.?\d*\s*(?:kg|lb|lbs))",
        }

        for vital_name, pattern in vital_patterns.items():
            matches = re.finditer(pattern, objective, re.IGNORECASE)
            for match in matches:
                findings.append({
                    "type": "vital",
                    "name": vital_name,
                    "value": match.group(1),
                })

        return findings

    @staticmethod
    def extract_evidence(soap_note: dict[str, str]) -> dict[str, Any]:
        """
        Extract all structured evidence from a complete SOAP note.
        
        Args:
            soap_note: {"subjective": "...", "objective": "...", "assessment": "...", "plan": "..."}
        
        Returns:
            {
                "diagnoses": [Diagnosis objects as dicts],
                "procedures": [Procedure objects as dicts],
                "symptoms": [list of symptoms],
                "findings": [list of vital/lab findings]
            }
        """
        assessment = soap_note.get("assessment", "")
        plan = soap_note.get("plan", "")
        subjective = soap_note.get("subjective", "")
        objective = soap_note.get("objective", "")

        diagnoses = EvidenceExtractor.extract_diagnoses(assessment)
        procedures = EvidenceExtractor.extract_procedures(plan)
        symptoms = EvidenceExtractor.extract_symptoms(subjective)
        findings = EvidenceExtractor.extract_findings(objective)

        return {
            "diagnoses": [d.to_dict() for d in diagnoses],
            "procedures": [p.to_dict() for p in procedures],
            "symptoms": symptoms,
            "findings": findings,
        }
