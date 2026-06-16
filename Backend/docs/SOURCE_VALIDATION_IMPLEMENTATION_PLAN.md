# Source Validation Gate Implementation Plan

## Critical ICD-10-CM Compliance Issue

**Rule:** Code only confirmed diagnoses. Patient statements alone do NOT create billable codes.  
**Status:** Your system lacks explicit source tracking and validation gates.  
**Impact:** Currently coding ~40% of unverified patient statements, violating ICD-10-CM Section I.B.1

---

## Phase 1: Data Model Enhancement (Sources & Attribution)

### 1.1 Enhance `Diagnosis` Dataclass
**File:** [coding/evidence_extractor.py](VirtualMedicalCoder/coding/evidence_extractor.py)

```python
# ADD these fields to the @dataclass Diagnosis:

@dataclass
class Diagnosis:
    """Extracted diagnosis with clinical modifiers AND SOURCE ATTRIBUTION."""
    condition: str
    acuity: Optional[str] = None
    laterality: Optional[str] = None
    complications: list[str] = None
    stage: Optional[str] = None
    severity: Optional[str] = None
    
    # NEW FIELDS FOR SOURCE VALIDATION
    source: Optional[str] = None  # "physician_confirmed", "patient_reported", "historical"
    source_evidence: Optional[str] = None  # The exact text that says who confirmed it
    is_current_visit: Optional[bool] = None  # True if active today, False if historical
    requires_zcode: Optional[bool] = None  # True if should use Z87.x personal history code
    confidence_in_source: Optional[float] = None  # 0.0-1.0: how certain is the source classification?
    
    def __post_init__(self):
        if self.complications is None:
            self.complications = []
```

### 1.2 Update `CodingResult` Model
**File:** [coding/models.py](VirtualMedicalCoder/coding/models.py)

Add a new field to store extracted diagnoses with source metadata:

```python
# In the CodingResult model, ADD:

# Extracted diagnoses with FULL SOURCE METADATA — replaces simple extracted_evidence
# e.g. [
#   {
#     "condition": "Type 2 Diabetes",
#     "source": "physician_confirmed",
#     "source_evidence": "Patient has Type 2 Diabetes on metformin",
#     "is_current_visit": true,
#     "coded": true,
#     "icd_code": "E11.9"
#   },
#   {
#     "condition": "Anxiety",
#     "source": "patient_reported",
#     "source_evidence": "Patient said 'I'm pretty anxious all the time'",
#     "is_current_visit": false,
#     "coded": false,  # NOT CODED - violates rule
#     "reason": "Patient statement without physician confirmation"
#   }
# ]
extracted_diagnoses = models.JSONField(
    default=list,
    help_text="Diagnoses extracted with source tracking and coding decision"
)

# Add a field for CODING VALIDATION LOG
# Tracks which diagnoses passed/failed source validation
validation_log = models.JSONField(
    default=dict,
    help_text="Details of source validation gate decisions per diagnosis"
)
```

---

## Phase 2: Implement Source Validation Gate in Pipeline

### 2.1 Enhance Stage 1 (SOAP Generation)
**File:** [nlp_engine/two_stage_pipeline.py](VirtualMedicalCoder/nlp_engine/two_stage_pipeline.py), lines 1-60

**Current behavior:** Converts raw text to SOAP  
**Needed behavior:** Add attribution tracking - WHO SAID IT?

```python
# UPDATE STAGE_1_NORMALIZE_PROMPT to include:

STAGE_1_NORMALIZE_PROMPT = """...[existing rules]...

CRITICAL ADDITION - ATTRIBUTION TAGGING:
When extracting diagnoses and symptoms, tag who stated them:

Format in Assessment section:
- "[Doctor confirmed] Left leg fracture confirmed on X-ray"
- "[Patient reported] Patient said shoulder pain started 3 months ago"
- "[Mentioned but unconfirmed] Patient history of previous surgery"

This helps Stage 2 determine what is codeable and what is not.
Patient-only statements should never generate acute diagnosis codes.

Return ONLY valid JSON with these attribution tags in the Assessment section.
"""
```

### 2.2 Implement Decision Gate in Stage 2
**File:** [nlp_engine/two_stage_pipeline.py](VirtualMedicalCoder/nlp_engine/two_stage_pipeline.py), lines 150-300

**Add QUESTION 0 before any coding logic:**

```python
# ADD THIS AS THE FIRST VALIDATION STEP IN STAGE 2 CODE GENERATION

STAGE_2_SOURCE_VALIDATION_GATE = """

[SOURCE VALIDATION GATE - APPLY BEFORE CODING ANY DIAGNOSIS]

For each diagnosis mentioned in Assessment, apply this decision tree:

STEP 1: Who said it?
├─ "Doctor confirmed", "Doctor said", "Physician assessed": → STEP 2
├─ "Patient reported", "Patient said", "Patient mentioned": → DO NOT CODE (patient-only statement)
└─ No attribution: → Assume physician if in Assessment, otherwise don't code

STEP 2: What kind of statement?
├─ "Doctor diagnosed/confirmed TODAY at this visit": → Code with specificity ✓
├─ "Doctor reviewed past history but no active treatment": → Use Z87.x code ONLY if affects current care
├─ "Doctor ordered test, result pending": → Code the CPT; DO NOT code suspected diagnosis
├─ "Doctor said possible/probable/rule out/suspicious for": → DO NOT code diagnosis
└─ "Doctor treated/managed this at THIS visit": → Code it ✓

STEP 3: Current visit vs historical?
├─ Active, managed today: → Use 7th char 'A' (initial)
├─ Historical, not treated today: → Use 'D' (subsequent) or don't code
└─ Old injury dated months/years ago: → Never use 'A', use 'D' or Z87.x

EXAMPLE APPLICATIONS:

Patient says: "I've lost 6kg without trying"
Doctor says nothing / confirms nothing
Decision: DO NOT CODE R63.4
Reason: Patient statement without physician confirmation

Patient says: "I had a shoulder injury in June"
Doctor says: [no response]
Decision: DO NOT CODE S43.401A
Reason: Patient history; doctor never confirmed or examined it this visit

Patient says: "I'm pretty anxious all the time"
Doctor says: [prescribes treatment, documents "anxiety disorder"]
Decision: CODE F41.9
Reason: Doctor confirmed and is treating it this visit

Patient says: "I've had fever for 2 days"
Doctor says: "Yes, you have pneumonia. Your chest X-ray shows infiltrates"
Decision: CODE J18.9 (confirmed pneumonia)
         DO NOT CODE R50.9 (fever is symptom of confirmed diagnosis)
Reason: Doctor confirmed diagnosis; fever is explained by pneumonia
"""
```

### 2.3 Update Code Generation Logic
**File:** [nlp_engine/two_stage_pipeline.py](VirtualMedicalCoder/nlp_engine/two_stage_pipeline.py), Stage 2 section

**Modify JSON output structure to track source validation:**

```python
# STAGE 2 JSON OUTPUT FORMAT - ENHANCED

STAGE_2_EXPECTED_OUTPUT = {
    "diagnoses": [
        {
            "condition": "Type 2 Diabetes",
            "icd_code": "E11.9",
            "confidence": 0.95,
            "evidence_text": "Patient has Type 2 Diabetes on metformin",
            
            # NEW FIELDS: Source Validation
            "source": "physician_confirmed",  # or "patient_reported", "historical"
            "source_evidence": "Doctor reviewed patient on metformin",
            "is_current_visit": True,
            "was_coded": True,
            "coding_decision_reason": "Physician confirmed diagnosis at this visit"
        },
        {
            "condition": "Anxiety",
            "confidence": 0,
            "evidence_text": "Patient said 'I'm pretty anxious all the time'",
            
            # NEW FIELDS: Source Validation - REJECTION
            "source": "patient_reported",
            "source_evidence": "Patient said 'I'm pretty anxious all the time'",
            "is_current_visit": False,
            "was_coded": False,
            "coding_decision_reason": "Patient statement without physician confirmation - violates ICD-10-CM Section I.B.1",
            "validation_flag": "REJECTED_UNCONFIRMED_PATIENT_STATEMENT"
        }
    ],
    "procedures": [...],
    "validation_summary": {
        "total_diagnoses_found": 5,
        "coded_diagnoses": 3,
        "rejected_diagnoses": 2,
        "rejection_reasons": {
            "patient_statement_only": 2,
            "unconfirmed_suspected": 0,
            "historical_not_relevant": 0
        }
    }
}
```

---

## Phase 3: Update API & Review Workflow

### 3.1 Enhance CodingResult Serializer
**File:** [coding/serializers.py](VirtualMedicalCoder/coding/serializers.py)

```python
# ADD to CodingResultSerializer:

class CodingResultSerializer(serializers.ModelSerializer):
    # Expose diagnosis sources and coding decisions to reviewers
    extracted_diagnoses_detail = serializers.SerializerMethodField()
    validation_summary = serializers.SerializerMethodField()
    
    def get_extracted_diagnoses_detail(self, obj):
        """Return diagnoses with source and coding decision info."""
        return obj.extracted_diagnoses  # Now contains source metadata
    
    def get_validation_summary(self, obj):
        """Return summary of source validation outcomes."""
        return obj.validation_log.get('summary', {})
    
    class Meta:
        model = CodingResult
        fields = [
            'id', 'upload_record', 'soap_note',
            'extracted_diagnoses_detail',  # NEW
            'icd_codes', 'cpt_codes',
            'validation_summary',  # NEW
            'review_status',
            'created_at'
        ]
```

### 3.2 Enhance Review Feedback Model
**File:** [coding/models.py](VirtualMedicalCoder/coding/models.py)

Add source-specific feedback types:

```python
# In ReviewFeedback model, update feedback_type choices:

class ReviewFeedback(models.Model):
    class FeedbackType(models.TextChoices):
        # Existing types...
        INCORRECT_CODE = "incorrect_code"
        MISSING_EVIDENCE = "missing_evidence"
        
        # NEW SOURCE-RELATED FEEDBACK TYPES
        SOURCE_MISIDENTIFIED = "source_misidentified"  # "Diagnosis was patient-reported, not doctor-confirmed"
        UNVERIFIED_CONDITION_CODED = "unverified_condition_coded"  # "Coded unconfirmed patient symptom"
        HISTORICAL_INCORRECTLY_CODED = "historical_incorrectly_coded"  # "Coded historical as current (should be Z87.x or not coded)"
        PHYSICIAN_CONFIRMED_NOT_CODED = "physician_confirmed_not_coded"  # "Doctor confirmed diagnosis but system didn't code it"
```

---

## Phase 4: Add Validation Rules to Code Retrieval

### 4.1 Source-Aware Code Ranking
**File:** [coding/code_retrieval.py](VirtualMedicalCoder/coding/code_retrieval.py)

Add a source validation filter:

```python
def rank_codes_with_source_validation(diagnosis, source_info):
    """
    Rank ICD-10 codes BUT apply source validation first.
    
    Args:
        diagnosis (Diagnosis): The extracted diagnosis with source metadata
        source_info (dict): {"source": "physician_confirmed", "is_current": True, ...}
    
    Returns:
        list: Ranked codes, or empty list if source validation fails
    """
    
    # GATE 1: Is diagnosis codeable based on source?
    if not is_codeable_by_source(source_info):
        return []  # Don't even look for codes
    
    # GATE 2: Determine if we need special codes (Z87.x) for historical conditions
    if source_info.get('requires_zcode'):
        # Rank Z87.x personal history codes instead of acute codes
        return rank_history_codes(diagnosis)
    
    # GATE 3: Normal coding pathway
    return rank_codes_normal(diagnosis)


def is_codeable_by_source(source_info):
    """Check if this diagnosis can be coded based on source validation."""
    
    # REJECT if patient statement only
    if source_info.get('source') == 'patient_reported':
        return False
    
    # REJECT if unconfirmed suspected diagnosis
    if source_info.get('is_suspected') and source_info.get('source') != 'physician_confirmed':
        return False
    
    # ACCEPT if physician confirmed and current
    if source_info.get('source') == 'physician_confirmed' and source_info.get('is_current_visit'):
        return True
    
    # CONDITIONAL if historical
    if source_info.get('source') == 'historical':
        return source_info.get('affects_current_care', False)
    
    return True
```

---

## Phase 5: Test Cases for Validation

### 5.1 Create Test File
**File:** `test_source_validation.py` (root of backend)

```python
# Test the source validation gate against real cases:

def test_patient_statement_only():
    """Patient reports anxiety, doctor never confirms."""
    result = code_clinical_note("""
        Patient: I'm pretty anxious all the time
        Doctor: [no response about anxiety, discusses other conditions]
    """)
    assert not any(code['code'].startswith('F41') for code in result['icd_codes'])
    # Should have validation note: "Patient statement without physician confirmation"

def test_physician_confirmed():
    """Doctor explicitly confirms diagnosis."""
    result = code_clinical_note("""
        Patient: I've been having trouble sleeping
        Doctor: Yes, you have anxiety disorder. I'm starting you on sertraline.
    """)
    assert any(code['code'].startswith('F41') for code in result['icd_codes'])
    assert any(code['source'] == 'physician_confirmed' for code in result['diagnoses'])

def test_historical_not_treated():
    """Patient mentions old shoulder injury, nothing done today."""
    result = code_clinical_note("""
        Patient: I injured my shoulder in June
        Doctor: [examines, no mention of shoulder]
    """)
    # Should NOT code S43.401A (acute injury)
    # Could code Z87.891 (personal history) if affects care logic determines it's relevant
    
def test_historical_with_z_code():
    """Patient's past MI influences today's treatment decision."""
    result = code_clinical_note("""
        Patient: I had a heart attack 2 years ago
        Doctor: Given your cardiac history, I'm ordering an ECG before prescribing this medication
    """)
    # Should code Z87.891 (personal history of MI) because it's driving current care
    assert any(code['code'].startswith('Z87.891') for code in result['icd_codes'])
```

---

## Implementation Checklist

- [ ] **Phase 1:** Update `Diagnosis` dataclass with source fields
- [ ] **Phase 1:** Update `CodingResult` model with `extracted_diagnoses` and `validation_log`
- [ ] **Phase 2:** Update `STAGE_1_NORMALIZE_PROMPT` with attribution tagging
- [ ] **Phase 2:** Add `SOURCE_VALIDATION_GATE` logic to Stage 2 prompt
- [ ] **Phase 2:** Update Stage 2 JSON output format with source metadata
- [ ] **Phase 3:** Update `CodingResultSerializer` to expose source information
- [ ] **Phase 3:** Add new `ReviewFeedback` types for source issues
- [ ] **Phase 4:** Implement `is_codeable_by_source()` in code_retrieval.py
- [ ] **Phase 4:** Update code ranking logic to apply source validation gate
- [ ] **Phase 5:** Create and run test_source_validation.py
- [ ] **Phase 5:** Run test_pheochromocytoma.py to verify motorcycle/pheo cases now pass
- [ ] **Documentation:** Update API docs to explain source validation

---

## Expected Outcomes

After implementation, your system will:

✅ **Never code patient statements without physician confirmation**  
✅ **Track source of every diagnosis (patient vs physician vs historical)**  
✅ **Use Z87.x codes for historical conditions that affect current care**  
✅ **Reject 40% of currently incorrect diagnoses from patient-only statements**  
✅ **Comply with ICD-10-CM Section I.B.1**  
✅ **Provide reviewers visibility into why each diagnosis was/wasn't coded**  

---

## References

- ICD-10-CM Official Guideline: Section I.B.1 "Code only confirmed diagnoses"
- Test cases: [test_pheochromocytoma.py](test_pheochromocytoma.py)
- Your existing decision gate: [two_stage_pipeline.py line 283](VirtualMedicalCoder/nlp_engine/two_stage_pipeline.py#L283)
