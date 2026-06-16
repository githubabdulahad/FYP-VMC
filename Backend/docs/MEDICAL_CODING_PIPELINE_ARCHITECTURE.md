# Virtual Medical Coder: Medical Coding Pipeline Architecture

## Executive Summary

The pipeline converts clinical narratives into structured SOAP notes and ICD-10/CPT codes through a **two-stage LLM process** with evidence-based validation. The system currently **lacks explicit distinction between physician-confirmed diagnoses vs patient statements vs unverified history**.

---

## 1. HIGH-LEVEL PIPELINE FLOW

```
┌─────────────────────────────────────────────────────────────────┐
│ USER UPLOADS CLINICAL TEXT                                      │
│ (PDF, image OCR, audio transcript, or direct text input)        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ INGESTION LAYER: Extract & Normalize                            │
│ (File extraction, text cleaning)                                │
│ [Location: ingestion/views.py, ingestion/models.py]            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ NLP ENGINE STAGE 1: Raw Text → Clean SOAP                      │
│ LLM normalizes messy/conversational text into structured SOAP   │
│ [Location: nlp_engine/two_stage_pipeline.py:stage_1_normalize] │
│ [System Prompt: STAGE_1_NORMALIZE_PROMPT]                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ NLP ENGINE STAGE 2: Clean SOAP → Codes                         │
│ LLM generates ICD-10 & CPT codes with confidence scores        │
│ [Location: nlp_engine/two_stage_pipeline.py:stage_2_generate]  │
│ [System Prompt: STAGE_2_CODE_GENERATION_PROMPT]                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ EVIDENCE EXTRACTION & VALIDATION                                │
│ Structures evidence from SOAP; validates codes against CSV DBs  │
│ [Location: coding/evidence_extractor.py]                       │
│ [Location: nlp_engine/services.py:analyze_raw_text]            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ CODE STORAGE & HUMAN REVIEW                                     │
│ CodingResult stores SOAP + codes + validation metadata          │
│ Reviewer approves/revises/rejects codes                         │
│ [Location: coding/models.py:CodingResult]                      │
│ [Location: coding/views.py:CodingReviewView]                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. COMPONENT DETAILS

### 2.1 Ingestion Layer

**File:** [ingestion/views.py](ingestion/views.py#L1)

**Endpoints:**
- `POST /api/ingestion/upload/` — Accept file URL, raw text, or file metadata
- `GET /api/ingestion/upload/<id>/` — Poll processing status

**Flow:**
1. User submits clinical document (PDF, image, text, audio transcript)
2. Backend creates `UploadRecord` with status = `PENDING`
3. Queues async task `process_upload_async` via Celery
4. Returns HTTP 202 immediately (async processing)

**Data Model:** [ingestion/models.py](ingestion/models.py#L1)
- `UploadRecord` → tracks file metadata, extraction progress, extracted text

---

### 2.2 NLP Engine: Two-Stage Pipeline

**Primary File:** [nlp_engine/two_stage_pipeline.py](nlp_engine/two_stage_pipeline.py#L1)

#### **Stage 1: Raw Text → Clean SOAP**

**Class:** `TwoStagePipeline.stage_1_normalize_to_soap()`

**Input:** Messy clinical text (conversation, dictation, fragmented notes, mixed formats)

**Process:**
1. LLM receives `STAGE_1_NORMALIZE_PROMPT` (line 10)
2. LLM extracts clinically relevant facts:
   - `[SYMPTOMS]` — patient-reported complaints
   - `[VITALS]` — BP, HR, temp, SpO2, labs
   - `[EXAM]` — physician observations
   - `[DIAGNOSES]` — explicitly stated conditions
   - `[PROCEDURES]` — interventions performed/ordered
   - `[MEDICATIONS]` — drugs prescribed
   - `[HISTORY]` — past medical/surgical history
   - `[PLAN]` — follow-up, tests ordered, discharge instructions

3. **Applies Negation/Uncertainty Filter** (STAGE_1_NORMALIZE_PROMPT, line 42):
   - **DO NOT CODE:** "no", "denies", "without", "negative for", "ruled out", "possible", "suspected", "rule out"
   - **ONLY CODE:** "confirmed", "diagnosis:", "acute", "chronic", "presents with", "positive for"

4. **Builds Structured SOAP:**
   ```json
   {
     "subjective": "Patient-reported symptoms and complaints",
     "objective": "Vitals, exam findings, lab/imaging results",
     "assessment": "Confirmed diagnoses ONLY",
     "plan": "Treatments, medications, procedures ordered, follow-up"
   }
   ```

**Output:** Clean SOAP JSON

**Key Rules:**
- No section left blank — uses "Not documented" placeholder if needed
- **[Initial/Follow-up Visit Detection]** — LLM adds "[Initial visit]" or "[Follow-up visit]" tag to help Stage 2 select correct E/M codes (line 58)

#### **Stage 2: Clean SOAP → Codes**

**Class:** `TwoStagePipeline.stage_2_generate_codes()`

**Input:** Clean SOAP JSON from Stage 1

**Process:**
1. LLM receives `STAGE_2_CODE_GENERATION_PROMPT` (line 82)
2. **Evidence-Code Matching** (line 91):
   - Each code MUST have `evidence_text` directly from the SOAP
   - Prevents coding wrong body parts (e.g., left vs right)
   - Example: ❌ "Code S81.812A (left leg) with evidence 'right arm cuts'" → ✅ "Code S81.812A with evidence 'left leg swelling'"

3. **Matching Accuracy Rules** (line 98):
   - Only code what is EXPLICITLY documented
   - Match anatomical sites EXACTLY (left leg code ≠ right arm)
   - Match laterality precisely

4. **Acuity Escalation Prevention** (line 131):
   - ⚠️ **Critical Rule:** Symptoms alone ≠ higher acuity diagnosis
   - Example: "SOB" alone ≠ COPD exacerbation → use J44.9 (unspecified), not J44.1
   - Requires explicit language: "acute exacerbation", "acute bronchitis", etc.

5. **Symptom Coding Decision Gate** (line 268):
   - **3 questions BEFORE coding any R-code or symptom:**
     1. Is symptom INTEGRAL to a confirmed diagnosis? (e.g., cough with pneumonia)
     2. Did PHYSICIAN explicitly diagnose it separately, or only patient reported?
     3. Is it routine/expected for the confirmed diagnosis?
   - ❌ Code only if ALL THREE = NO
   - Examples:
     - Patient reports anxiety but no physician diagnosis → DO NOT code F41.9
     - Tachycardia with pheochromocytoma → integral symptom, DO NOT code R00.0

6. **Code Generation by Type:**
   - **S-codes (Trauma):** Injuries with 7th character A (initial), D (subsequent), S (sequela)
   - **E-codes:** Metabolic (diabetes, metabolic disorders)
   - **I-codes:** Circulatory (hypertension, heart disease)
   - **J-codes:** Respiratory (asthma, COPD)
   - **Z-codes:** Status/long-term medication use
   - **CPT (E/M codes):** 99202-99205 (new patient), 99212-99215 (established)
   - **CPT (Procedures):** Only PERFORMED procedures, not planned
   - **CPT (Labs):** Only if results documented or explicitly ordered

7. **Confidence Scoring** (line 437):
   ```
   1.00 → Exact diagnosis/procedure name present verbatim
   0.85 → Strong clinical indicators present
   0.70 → Inferred from contextual clues only
   ```
   - Must include `confidence_reason` explaining score

**Output:** 
```json
[
  {
    "system": "ICD10",
    "code": "E11.9",
    "description": "Type 2 diabetes mellitus without complications",
    "confidence": 0.95,
    "confidence_reason": "Explicitly documented in assessment",
    "evidence_text": "Type 2 diabetes with control"
  },
  {
    "system": "CPT",
    "code": "99213",
    "description": "Office visit, established patient, straightforward",
    "confidence": 0.85,
    "evidence_text": "Follow-up visit"
  }
]
```

---

### 2.3 Evidence Extraction

**File:** [coding/evidence_extractor.py](coding/evidence_extractor.py#L1)

**Classes & Methods:**
- `Diagnosis` dataclass → condition, acuity, laterality, complications, stage, severity
- `Procedure` dataclass → name, approach, site, laterality, urgency
- `EvidenceExtractor.extract_diagnoses()` → parses assessment section into structured diagnoses
- `EvidenceExtractor.extract_procedures()` → parses plan section into structured procedures
- `EvidenceExtractor.extract_symptoms()` → extracts reported symptoms from subjective

**Output Structure:**
```json
{
  "diagnoses": [
    {
      "condition": "Type 2 Diabetes",
      "acuity": "chronic",
      "severity": null,
      "laterality": null,
      "complications": [],
      "stage": null
    }
  ],
  "procedures": [
    {
      "name": "CT scan abdomen",
      "approach": "imaging",
      "site": "abdomen",
      "laterality": null,
      "urgency": null
    }
  ],
  "symptoms": ["fatigue", "polyuria"]
}
```

---

### 2.4 Code Validation & Correction

**File:** [nlp_engine/services.py](nlp_engine/services.py#L1)

**Function:** `analyze_raw_text()` (orchestrates full pipeline)

**Validation Pipeline:**
1. **Database Lookup:** Check if ICD-10/CPT code exists in local CSV tables
2. **Format Validation:** Verify code format (ICD-10 pattern, CPT pattern)
3. **Auto-Correction:**
   - Single-view imaging → multi-view standard (e.g., 71045 → 71046)
   - Invalid codes with low confidence → suggest best match via `CodeRetriever`
4. **Flagging for Review:**
   - Valid format but not in database + high confidence → flag for review
   - Evidence-code mismatch → flag (via `CodeRetriever.flag_codes_for_review()`)

**Output:** `validation_metadata`
```json
{
  "total_codes": 8,
  "flagged_count": 2,
  "auto_corrected_count": 1,
  "needs_review": true,
  "validation_issues": [
    {
      "code": "E11.65",
      "system": "ICD10",
      "issue": "Valid format but not in database"
    }
  ]
}
```

---

### 2.5 Code Retrieval & Ranking

**File:** [coding/code_retrieval.py](coding/code_retrieval.py#L1)

**Key Method:** `CodeRetriever.retrieve_icd_candidates(diagnosis_text)`

**Algorithm:**
1. Tokenizes evidence text
2. Compares to ICD-10 codes in `validator.icd10_db`
3. Calculates relevance score (0.0–1.0) based on:
   - Token matching (70% weight)
   - Phrase matching (30% weight)
4. Returns top-K candidates sorted by relevance

**Used For:**
- Alternative code suggestions during human review
- Auto-correction when LLM-generated codes are invalid

---

### 2.6 Diagnosis Mapping & Extraction

**Files:**
- [coding/diagnosis_parser.py](coding/diagnosis_parser.py#L1)
- [coding/diagnosis_mapper.py](coding/diagnosis_mapper.py#L1)

#### **diagnosis_parser.py**

**Class:** `ClinicalNarrativeParser`

**Detects:**
- **Trauma/Injuries:** Keywords (fracture, laceration, wound, etc.), body parts, laterality, severity
- **Chronic Conditions:** Keywords (diabetes, hypertension, asthma, arthritis)
- **Acute Conditions:** Keywords (acute, sudden, new onset)
- **Procedures:** Surgery, imaging, injections, physical therapy

**Output:** `ExtractedDiagnosis` objects with:
- `diagnosis_name`, `diagnosis_type` (TRAUMA_INJURY, CHRONIC_CONDITION, etc.)
- `primary_location`, `laterality`, `severity`, `acuity`
- `icd_category` (S, E, I, J, etc.)
- `confidence`

#### **diagnosis_mapper.py**

**Class:** `DiagnosisToCodeMapper`

**Maps:**
- Trauma diagnoses → ICD-10 S-codes (injuries)
- Conditions → ICD-10 E/I/J codes (metabolic, circulatory, respiratory)
- Mechanisms → External cause codes (V/W/X/Y codes)

**Example:**
```python
("laceration", "arm", "right") → ["S51.811A"]  # ICD-10 for open wound right forearm
("type 2 diabetes", None, None) → ["E11.9"]
```

---

### 2.7 Human Review & Feedback

**File:** [coding/views.py](coding/views.py#L1)

**Endpoints:**
- `GET /api/coding/` — List all coding results for user
- `GET /api/coding/<id>/` — Get one result
- `POST /api/coding/<id>/review/` — Reviewer approves/revises codes
- `GET /api/coding/<id>/feedback/` — Feedback history
- `POST /api/coding/<id>/alternatives/` — Get alternative code suggestions

**Review Workflow:**
```
CodingResult (status=PENDING)
    ↓
Reviewer reviews SOAP + codes
    ↓
Reviewer decides: APPROVED | REJECTED | REVISED
    ↓
If REVISED:
    - Reviewer supplies corrected codes
    - ReviewFeedback record created
    - Codes updated
    ↓
CodingResult (status=APPROVED | REJECTED | REVISED)
```

**Data Model:** [coding/models.py](coding/models.py#L1)
- `CodingResult` → stores SOAP, codes, validation metadata, review status
- `ReviewFeedback` → tracks what codes were corrected and why (for ML improvement)

---

## 3. CURRENT ARCHITECTURE: DIAGNOSIS SOURCE DISTINCTION

### ✅ Currently Implemented

**Negation/Uncertainty Detection (Stage 1):**
- Filters out conditions with uncertainty language
- [STAGE_1_NORMALIZE_PROMPT, line 42](nlp_engine/two_stage_pipeline.py#L42)
- Keywords: "possible", "suspected", "rule out", "may be", "cannot exclude", "differential"

**Physician Confirmation Logic (Stage 2):**
- **Question 2** in Symptom Coding Decision Gate (line 283):
  - "Did the PHYSICIAN explicitly diagnose/confirm this as a separate diagnosis, or did only the PATIENT report it?"
  - Examples:
    - ❌ Patient reports anxiety but no physician diagnosis → DO NOT code F41.9
    - ❌ Patient says "I'm tired" without physician assessment → DO NOT code R53.1
    - ✅ Doctor: "You have diabetic neuropathy" → code it

**Historical vs Current Distinction (Stage 2):**
- 7th character encoding:
  - 'A' = initial encounter (current, being treated)
  - 'D' = subsequent encounter (follow-up, routine)
  - 'S' = sequela (late effect of old injury)
- Example: "History of shoulder injury from June 2025" → S43.4xxD (not A)

### ❌ Missing / Needs Enhancement

**No Explicit Field for Diagnosis Source in Data Models:**
- `CodingResult` model stores SOAP and codes but has NO `diagnosis_source` field
- `Diagnosis` dataclass in `evidence_extractor.py` has NO `source` or `confirmation_status` field
- Reviewers cannot easily see which diagnoses came from patient vs physician

**No Structured Capture of:**
- Is this diagnosis PATIENT-STATED or PHYSICIAN-CONFIRMED?
- Is this from CURRENT VISIT or HISTORICAL past medical history?
- Which diagnoses came from REVIEW OF RECORDS vs DIRECT OBSERVATION?

**No Feedback Loop for Source Misclassification:**
- `ReviewFeedback` model has NO field to track when source was misidentified
- No mechanism to improve LLM's future source detection

**LLM Prompts Assume Single Voice:**
- Stage 1 normalizes "Doctor: ... Patient: ..." into SOAP
- Loses track of WHO SAID WHAT
- By Stage 2, LLM doesn't know if "Patient reports anxiety" vs "Doctor diagnosed anxiety"

---

## 4. WHERE TO ADD PATIENT STATEMENT vs PHYSICIAN CONFIRMATION DISTINCTION

### Location 1: Diagnosis Extraction → Add Source Metadata

**File:** [coding/evidence_extractor.py](coding/evidence_extractor.py#L17)

**Current:**
```python
@dataclass
class Diagnosis:
    condition: str
    acuity: Optional[str] = None
    laterality: Optional[str] = None
    complications: list[str] = None
    stage: Optional[str] = None
    severity: Optional[str] = None
```

**Needed Enhancement:**
```python
@dataclass
class Diagnosis:
    condition: str
    acuity: Optional[str] = None
    laterality: Optional[str] = None
    complications: list[str] = None
    stage: Optional[str] = None
    severity: Optional[str] = None
    # NEW FIELDS:
    source: Literal["physician_confirmed", "patient_stated", "historical"] = "physician_confirmed"
    is_current: bool = True  # Current visit vs historical
    source_evidence: Optional[str] = None  # Exact quote showing source
    confidence_in_source: float = 0.95  # How confident is extraction of source?
```

### Location 2: NLP Stage 1 → Preserve Source Information

**File:** [nlp_engine/two_stage_pipeline.py](nlp_engine/two_stage_pipeline.py#L10)

**Current Problem:**
- Stage 1 normalizes dialogue "Doctor: X Patient: Y" into SOAP sections
- Loses who said what
- By Stage 2, "Patient reports anxiety" vs "Doctor diagnosed anxiety" looks identical

**Enhancement Needed:**
- Add a 5th SOAP section: `"ATTRIBUTION"` that tracks source for each finding
- Example:
  ```json
  {
    "subjective": "Patient reports anxiety and fatigue",
    "objective": "BP 140/90, HR 88",
    "assessment": "Type 2 diabetes, hypertension",
    "plan": "Continue metformin, recheck BP in 2 weeks",
    "attribution": {
      "Type 2 diabetes": "physician_confirmed",
      "hypertension": "physician_confirmed",
      "anxiety": "patient_stated_not_physician_confirmed",
      "fatigue": "patient_stated_not_physician_confirmed",
      "BP 140/90": "objective_finding"
    }
  }
  ```

### Location 3: Stage 2 Code Generation → Use Attribution

**File:** [nlp_engine/two_stage_pipeline.py](nlp_engine/two_stage_pipeline.py#L82)

**Current:**
- STAGE_2_CODE_GENERATION_PROMPT assumes all diagnoses in Assessment are codable
- No explicit check: "Is this physician-confirmed or patient-stated?"

**Enhancement Needed:**
- After the Symptom Coding Decision Gate (line 268), add source check:
  ```
  QUESTION 0 (NEW): Is this diagnosis PHYSICIAN-CONFIRMED or just PATIENT-STATED?
    - If diagnosis attributed to patient statement only → DO NOT CODE
    - If attributed to physician confirmation → code it
    - If historical past medical history → apply lower confidence, use D/S timing
  ```

### Location 4: CodingResult Model → Store Source Metadata

**File:** [coding/models.py](coding/models.py#L18)

**Current:**
```python
class CodingResult(models.Model):
    soap_note = models.JSONField(default=dict)
    icd_codes = models.JSONField(default=list)
    cpt_codes = models.JSONField(default=list)
```

**Needed Enhancement:**
```python
class CodingResult(models.Model):
    soap_note = models.JSONField(default=dict)
    # NEW: Structured diagnoses with source info
    extracted_diagnoses = models.JSONField(
        default=list,
        help_text="[{condition, acuity, source, is_current, source_evidence}, ...]"
    )
    icd_codes = models.JSONField(default=list)
    cpt_codes = models.JSONField(default=list)
```

**Example stored format:**
```json
{
  "extracted_diagnoses": [
    {
      "condition": "Type 2 Diabetes",
      "source": "physician_confirmed",
      "is_current": true,
      "source_evidence": "Diagnosis documented in Assessment section",
      "coded_as": "E11.9"
    },
    {
      "condition": "Anxiety",
      "source": "patient_stated",
      "is_current": true,
      "source_evidence": "Patient reports anxiety but no physician assessment",
      "coded_as": null,
      "coding_decision": "Not coded per symptom coding gate"
    },
    {
      "condition": "Shoulder injury",
      "source": "historical",
      "is_current": false,
      "source_evidence": "History of shoulder injury from June 2025",
      "coded_as": "S43.4xxD"
    }
  ]
}
```

### Location 5: Review Workflow → Display Source to Reviewer

**File:** [coding/views.py](coding/views.py#L16)

**Enhancement Needed:**
- Expand `CodingResultSerializer` to include diagnosis sources
- Display to reviewer:
  - Which diagnoses are physician-confirmed vs patient-stated vs historical
  - Why certain diagnoses were NOT coded
  - Suggested corrections if source was misidentified

**Example API Response:**
```json
{
  "id": 123,
  "soap_note": {...},
  "extracted_diagnoses": [
    {
      "condition": "Type 2 Diabetes",
      "source": "physician_confirmed",
      "coded_as": "E11.9",
      "confidence": 0.95
    },
    {
      "condition": "Anxiety",
      "source": "patient_stated",
      "coded_as": null,
      "not_coded_reason": "Patient reported but not physician-confirmed"
    }
  ],
  "icd_codes": [...],
  "review_status": "pending"
}
```

### Location 6: ReviewFeedback → Track Source Corrections

**File:** [coding/models.py](coding/models.py#L156)

**Current:**
```python
class ReviewFeedback(models.Model):
    feedback_type = models.CharField(
        choices=[
            ("missing_code", "Missing Code Added"),
            ("incorrect_code", "Code Corrected"),
            ...
        ]
    )
```

**Needed Enhancement:**
```python
feedback_type_choices = [
    ("missing_code", "Missing Code Added"),
    ("incorrect_code", "Code Corrected"),
    ("specificity", "Increased Specificity"),
    ("source_misidentified", "Source Misidentified"),  # NEW
    ("patient_statement_coded", "Patient Statement Incorrectly Coded"),  # NEW
    ...
]
```

This enables tracking when source attribution was wrong (for ML improvement).

---

## 5. DATA FLOW SUMMARY TABLE

| Component | Input | Process | Output | File Location |
|-----------|-------|---------|--------|---------------|
| **Ingestion** | PDF/image/text/audio | Extract text from file | `UploadRecord` + extracted_text | ingestion/views.py |
| **Stage 1 (SOAP)** | Raw clinical text | LLM normalizes to SOAP | Clean SOAP JSON | nlp_engine/two_stage_pipeline.py:stage_1 |
| **Stage 2 (Codes)** | Clean SOAP | LLM generates codes | ICD-10/CPT codes + confidence | nlp_engine/two_stage_pipeline.py:stage_2 |
| **Evidence Extract** | SOAP | Parse into structured evidence | Diagnoses, procedures, symptoms | coding/evidence_extractor.py |
| **Validation** | LLM codes | Check against CSV DB; auto-correct | Validated codes + flags | nlp_engine/services.py |
| **Storage** | Codes + SOAP | Store in DB | `CodingResult` | coding/models.py |
| **Review** | `CodingResult` | Human reviewer approves/revises | Updated codes | coding/views.py |

---

## 6. API ENDPOINTS SUMMARY

### Ingestion
- `POST /api/ingestion/upload/` — Submit clinical document
- `GET /api/ingestion/upload/<id>/` — Check processing status

### Coding Results
- `GET /api/coding/` — List user's coding results
- `GET /api/coding/<id>/` — Get one result
- `POST /api/coding/<id>/review/` — Submit reviewer feedback
- `GET /api/coding/<id>/feedback/` — View feedback history
- `POST /api/coding/<id>/alternatives/` — Get alternative code suggestions

---

## 7. KEY SYSTEM PROMPTS

### Stage 1: Normalize to SOAP
**Location:** [line 10](nlp_engine/two_stage_pipeline.py#L10)

Key rules:
- Extract only clinically relevant facts
- Apply negation/uncertainty filter
- Group into SOAP sections
- Add visit type indicators (Initial/Follow-up)

### Stage 2: Generate Codes
**Location:** [line 82](nlp_engine/two_stage_pipeline.py#L82)

Key rules:
- Evidence-code matching (evidence text MUST match code)
- Matching accuracy (anatomical sites, laterality)
- Acuity escalation prevention
- Symptom coding decision gate
- Confidence scoring with reasoning

---

## NEXT STEPS FOR IMPLEMENTATION

1. **Add source field to Diagnosis dataclass** (evidence_extractor.py)
2. **Enhance Stage 1 prompt to capture attribution** (two_stage_pipeline.py)
3. **Update Stage 2 prompt with source-based coding rule** (two_stage_pipeline.py)
4. **Extend CodingResult model** to store extracted diagnoses with sources (models.py)
5. **Update ReviewFeedback** to track source corrections (models.py)
6. **Enhance API response** to expose source information to frontend (views.py)
7. **Add database migration** to support new fields

---

## CONFIGURATION & ENVIRONMENT

**LLM Configuration:**
- Primary: OpenRouter API (`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`)
- Fallback: Ollama local (`OLLAMA_FALLBACK_MODEL`)
- Default model: `deepseek/deepseek-chat`
- Default fallback: `qwen2.5:7b-instruct`

**Code Databases:**
- ICD-10: CSV table loaded into `validator.icd10_db`
- CPT: CSV table loaded into `validator.cpt_db`
- Token maps for relevance scoring: `validator.icd_tokens`, `validator.cpt_tokens`

**Validation Logic:**
- Format validation (regex patterns)
- Database lookup
- Auto-correction for common variants
- Confidence-based flagging

---

**Document Last Updated:** June 2026  
**System Version:** Two-Stage Pipeline with Evidence-Based Validation
