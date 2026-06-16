# Medical Coding Pipeline: Visual Architecture & Data Flow

## Complete System Flow Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         USER CLINICAL DOCUMENT                             │
│                (PDF, Image, Audio Transcript, Raw Text)                    │
└────────────────────┬───────────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                      INGESTION LAYER                                        │
│  POST /api/ingestion/upload/                                               │
│  • Receive file URL or raw text                                            │
│  • Create UploadRecord (status=PENDING)                                    │
│  • Queue async: process_upload_async (Celery task)                         │
│  • Return HTTP 202 Accepted                                                │
│                                                                             │
│  Files: ingestion/views.py, ingestion/models.py                            │
└────────────────────┬───────────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                   TEXT EXTRACTION & NORMALIZATION                          │
│  (Background task — Celery worker)                                         │
│  • Extract text from PDF/image (OCR) or use raw text                       │
│  • Clean up whitespace, normalize line breaks                              │
│  • Detect if input is dialogue-heavy (Doctor: ... Patient: ...)            │
│                                                                             │
│  UploadRecord.status = PROCESSING                                          │
│  UploadRecord.extracted_text = cleaned text                                │
└────────────────────┬───────────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                  NLP ENGINE: STAGE 1 (Raw → SOAP)                          │
│  TwoStagePipeline.stage_1_normalize_to_soap(raw_text)                      │
│                                                                             │
│  INPUT: Messy clinical text (conversation, fragmented notes, etc.)         │
│                                                                             │
│  PROCESS:                                                                   │
│  1. Send to LLM with STAGE_1_NORMALIZE_PROMPT                              │
│  2. LLM extracts clinically relevant facts:                                │
│     • [SYMPTOMS] — patient-reported complaints                             │
│     • [VITALS] — BP, HR, temp, SpO2, lab values                            │
│     • [EXAM] — physical examination findings                               │
│     • [DIAGNOSES] — explicitly stated conditions ONLY                      │
│     • [PROCEDURES] — interventions performed/ordered                       │
│     • [MEDICATIONS] — drugs prescribed                                     │
│     • [HISTORY] — past medical/surgical history                            │
│     • [PLAN] — follow-up, tests, discharge instructions                    │
│  3. Apply Negation/Uncertainty Filter:                                     │
│     ✗ DO NOT INCLUDE: "no", "denies", "suspected", "rule out"             │
│     ✓ ONLY INCLUDE: "confirmed", "diagnosis:", "acute", "chronic"         │
│  4. Detect visit type:                                                     │
│     — "[Initial visit]" if "What brings you in today?", "new patient"     │
│     — "[Follow-up visit]" if "follow-up", "established patient"           │
│  5. Structure into SOAP JSON                                               │
│                                                                             │
│  OUTPUT:                                                                    │
│  {                                                                          │
│    "subjective": "Patient reports fatigue x 2 weeks. Denies fever.",      │
│    "objective": "BP 140/90, HR 88, RR 16, T 98.6°F",                      │
│    "assessment": "Type 2 Diabetes, Hypertension. [Follow-up visit]",      │
│    "plan": "Continue metformin. Recheck BP in 2 weeks."                    │
│  }                                                                          │
│                                                                             │
│  File: nlp_engine/two_stage_pipeline.py (line 612–705)                   │
│  Prompt: STAGE_1_NORMALIZE_PROMPT (line 10)                               │
└────────────────────┬───────────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                  NLP ENGINE: STAGE 2 (SOAP → Codes)                        │
│  TwoStagePipeline.stage_2_generate_codes(clean_soap)                       │
│                                                                             │
│  INPUT: Clean SOAP JSON from Stage 1                                       │
│                                                                             │
│  PROCESS:                                                                   │
│  1. Send SOAP to LLM with STAGE_2_CODE_GENERATION_PROMPT                   │
│  2. LLM validates SOAP diagnoses:                                          │
│     • Only diagnoses from Assessment section (not Subjective)              │
│     • NEGATION FILTER: Exclude negated/uncertain conditions                │
│  3. For EACH confirmed diagnosis/procedure:                                │
│                                                                             │
│     A) ICD-10 CODE SELECTION:                                              │
│        Q1: Complication documented? → use complication subcode             │
│        Q2: Specific site/laterality? → use specific subcode                │
│        Q3: Acuity documented? → use acuity-specific subcode                │
│        Q4: 7th character timing:                                           │
│            — 'A' = initial encounter (current, being treated)              │
│            — 'D' = subsequent (follow-up, routine)                         │
│            — 'S' = sequela (late effect of old injury)                     │
│        Confidence score (0.0–1.0):                                         │
│            — 1.00: Exact diagnosis name verbatim in note                   │
│            — 0.85: Strong clinical indicators present                      │
│            — 0.70: Inferred from context                                   │
│                                                                             │
│     B) SYMPTOM CODING DECISION GATE (CRITICAL):                            │
│        ❌ QUESTION 1: Is symptom INTEGRAL to confirmed diagnosis?          │
│           (Cough with pneumonia = integral, do NOT code R05.1)             │
│        ❌ QUESTION 2: Did PHYSICIAN confirm separately?                    │
│           (Patient says "anxiety" but no physician diagnosis = NOT coded)   │
│        ❌ QUESTION 3: Is it routine/expected for existing diagnosis?       │
│           (Tachycardia with pheochromocytoma = routine, do NOT code)       │
│        → Code symptom ONLY if ALL THREE = NO                               │
│                                                                             │
│     C) CPT CODE SELECTION:                                                 │
│        — E/M: 99202–99205 (new patient) or 99212–99215 (established)       │
│        — Only PERFORMED procedures (not planned)                           │
│        — Labs: only if results documented or explicitly ordered            │
│        — Imaging: multi-view default (71046 not 71045)                     │
│        — Contrast: default to "with contrast" if not specified             │
│                                                                             │
│     D) EVIDENCE-CODE MATCHING (ABSOLUTELY CRITICAL):                       │
│        ✓ Each code MUST have evidence_text from SOAP                       │
│        ✓ evidence_text MUST match code's body part/site                    │
│        ✓ Example:                                                           │
│          Code: S81.812A (left leg open wound)                              │
│          Evidence: "Deep cuts on left leg"  ← MATCHES ✓                    │
│          NOT: "cuts on right arm"  ← MISMATCH ✗                            │
│                                                                             │
│  OUTPUT:                                                                    │
│  [                                                                          │
│    {                                                                        │
│      "system": "ICD10",                                                    │
│      "code": "E11.9",                                                      │
│      "description": "Type 2 diabetes mellitus without complications",      │
│      "confidence": 0.95,                                                   │
│      "confidence_reason": "Explicitly documented in Assessment",           │
│      "evidence_text": "Type 2 Diabetes"                                    │
│    },                                                                       │
│    {                                                                        │
│      "system": "CPT",                                                      │
│      "code": "99214",                                                      │
│      "description": "Office visit, established patient, MDM moderate",     │
│      "confidence": 0.85,                                                   │
│      "evidence_text": "Follow-up visit"                                    │
│    }                                                                        │
│  ]                                                                          │
│                                                                             │
│  File: nlp_engine/two_stage_pipeline.py (line 706–780)                   │
│  Prompt: STAGE_2_CODE_GENERATION_PROMPT (line 82)                         │
└────────────────────┬───────────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│              EVIDENCE EXTRACTION & STRUCTURED PARSING                      │
│  EvidenceExtractor.extract_evidence(clean_soap)                            │
│                                                                             │
│  Parses SOAP into structured evidence:                                     │
│  • extract_diagnoses() → Assessment → Diagnosis objects                    │
│  • extract_procedures() → Plan → Procedure objects                         │
│  • extract_symptoms() → Subjective → symptom list                          │
│                                                                             │
│  OUTPUT:                                                                    │
│  {                                                                          │
│    "diagnoses": [                                                          │
│      {                                                                      │
│        "condition": "Type 2 Diabetes",                                     │
│        "acuity": "chronic",                                                │
│        "laterality": null,                                                 │
│        "complications": [],                                                │
│        "stage": null,                                                      │
│        "severity": null                                                    │
│      }                                                                      │
│    ],                                                                       │
│    "procedures": [...],                                                    │
│    "symptoms": ["fatigue"]                                                 │
│  }                                                                          │
│                                                                             │
│  File: coding/evidence_extractor.py                                        │
└────────────────────┬───────────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                 CODE VALIDATION & AUTO-CORRECTION                          │
│  analyze_raw_text() in nlp_engine/services.py                             │
│                                                                             │
│  For each LLM-generated code:                                              │
│  1. Database lookup: Is code in validator.icd10_db or cpt_db?              │
│  2. Format validation: Does code match ICD-10/CPT pattern?                 │
│  3. Auto-corrections:                                                      │
│     • Single-view imaging → multi-view standard (71045 → 71046)            │
│     • Invalid format + low confidence → find best match via CodeRetriever  │
│  4. Flagging for review:                                                   │
│     • Valid format but not in DB + high confidence → FLAG                  │
│     • Evidence-code mismatch → FLAG (via CodeRetriever)                    │
│     • Low confidence → FLAG                                                │
│                                                                             │
│  OUTPUT: validation_metadata                                               │
│  {                                                                          │
│    "total_codes": 8,                                                       │
│    "flagged_count": 2,                                                     │
│    "auto_corrected_count": 1,                                              │
│    "needs_review": true,                                                   │
│    "validation_issues": [...]                                              │
│  }                                                                          │
│                                                                             │
│  File: nlp_engine/services.py (line 582–805)                              │
└────────────────────┬───────────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    SAVE CODING RESULT TO DATABASE                          │
│                                                                             │
│  Create CodingResult:                                                      │
│  • upload_record → FK to UploadRecord                                      │
│  • user → FK to logged-in User                                             │
│  • soap_note → JSON (subjective, objective, assessment, plan)              │
│  • extracted_evidence → JSON (diagnoses, procedures, symptoms)             │
│  • icd_codes → JSON list (validated ICD-10 codes)                          │
│  • cpt_codes → JSON list (validated CPT codes)                             │
│  • validation_metadata → JSON (flagged codes, issues, suggestions)         │
│  • review_status → "pending" (awaiting human review)                       │
│  • confidence → overall LLM confidence (0.0–1.0)                           │
│                                                                             │
│  UploadRecord.status = COMPLETED                                           │
│                                                                             │
│  File: coding/models.py:CodingResult                                      │
└────────────────────┬───────────────────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                      HUMAN REVIEW WORKFLOW                                 │
│                                                                             │
│  GET /api/coding/<id>/  → Reviewer retrieves CodingResult                  │
│  Reviewer sees:                                                            │
│  • SOAP note (subjective, objective, assessment, plan)                     │
│  • Auto-generated codes (ICD-10, CPT)                                      │
│  • Validation issues & flags                                               │
│                                                                             │
│  POST /api/coding/<id>/review/                                             │
│  Reviewer actions:                                                         │
│  ├─ APPROVE → Accept as-is → review_status = "approved"                   │
│  ├─ REJECT → Do not use codes → review_status = "rejected"                │
│  └─ REVISE → Correct codes → review_status = "revised"                    │
│                                                                             │
│  If REVISED:                                                               │
│  • Reviewer supplies corrected icd_codes & cpt_codes                       │
│  • Create ReviewFeedback record (for ML improvement):                      │
│    - llm_codes → what LLM generated                                        │
│    - corrected_codes → what reviewer changed to                            │
│    - feedback_type → why (missing_code, incorrect_code, etc.)             │
│    - explanation → additional context                                      │
│                                                                             │
│  POST /api/coding/<id>/alternatives/                                       │
│  For any diagnosis, get alternative code suggestions via CodeRetriever     │
│  (used during review to find correct codes)                                │
│                                                                             │
│  File: coding/views.py (CodingReviewView, CodeAlternativesView)            │
│  File: coding/models.py (ReviewFeedback)                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Interaction Diagram

```
┌─────────────────────────────────┐
│  ingestion/views.py             │
│  FileUploadView                 │  ← User uploads clinical document
├─────────────────────────────────┤
│ Creates UploadRecord(pending)    │
│ Queues: process_upload_async    │
└────────────┬────────────────────┘
             │
             │ (Celery task)
             ▼
┌─────────────────────────────────┐
│  ingestion/tasks.py             │
│  process_upload_async()         │  ← Background extraction
├─────────────────────────────────┤
│ Extract text from file          │
│ Call: _run_nlp_and_save()       │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│  nlp_engine/services.py                         │
│  analyze_raw_text(raw_text)                     │  ← Orchestrates pipeline
├─────────────────────────────────────────────────┤
│ 1. TwoStagePipeline.process_complete()          │
│    ├─ Stage 1: normalize_to_soap()              │
│    └─ Stage 2: generate_codes()                 │
│ 2. EvidenceExtractor.extract_evidence()         │
│ 3. CodeRetriever.flag_codes_for_review()        │
│ 4. validator.validate_code() (all codes)        │
│ 5. Returns: {soap, codes, evidence, metadata}   │
└────────────┬─────────────────────────────────────┘
             │
    ┌────────┴──────────┬──────────────┬────────────┐
    │                   │              │            │
    ▼                   ▼              ▼            ▼
┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌───────┐
│ Stage 1      │  │ Stage 2      │  │Evidence  │  │Code   │
│ (SOAP)       │  │ (Codes)      │  │Extract   │  │Valid. │
├──────────────┤  ├──────────────┤  ├──────────┤  ├───────┤
│TwoStage      │  │TwoStage      │  │Evidence  │  │Validator
│Pipeline      │  │Pipeline      │  │Extractor │  │(CSV DBs)
│             │  │             │  │         │  │
│→LLM call    │  │→LLM call    │  │→Parse   │  │→Check
│→JSON parse  │  │→JSON parse  │  │SOAP    │  │→Flag
└──────────────┘  └──────────────┘  └──────────┘  └───────┘
    Returns:          Returns:       Returns:    Returns:
    {subject...}      [{system,      {diagnoses  validation
                       code...}]      procedures} metadata
             │
             └──────────────┬─────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────┐
│  coding/models.py                           │
│  CodingResult.objects.create()              │  ← Save to DB
├─────────────────────────────────────────────┤
│ upload_record, user, soap_note              │
│ extracted_evidence, icd_codes, cpt_codes    │
│ validation_metadata, review_status=pending  │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│  coding/views.py                            │
│  CodingResultListView / DetailView          │  ← Reviewer retrieves result
├─────────────────────────────────────────────┤
│ GET /api/coding/                            │
│ GET /api/coding/<id>/                       │
│ Returns: CodingResult + all codes + metadata│
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│  coding/views.py                            │
│  CodingReviewView                           │  ← Human review
├─────────────────────────────────────────────┤
│ POST /api/coding/<id>/review/               │
│ • Approve/Reject/Revise                     │
│ • If Revise: provide corrected codes        │
│ • Create ReviewFeedback record              │
└────────────┬────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────┐
│  coding/models.py                           │
│  ReviewFeedback.objects.create()            │  ← ML feedback loop
├─────────────────────────────────────────────┤
│ llm_codes, corrected_codes                  │
│ feedback_type, explanation                  │
└─────────────────────────────────────────────┘

Alternative Path (during review):
  POST /api/coding/<id>/alternatives/ → CodeRetriever.retrieve_icd_candidates()
  ↓
  CodeRetriever searches validator.icd10_db for matching codes
  ↓
  Returns ranked candidates to reviewer
```

---

## Evidence Flow: From Text to Structured Data

```
Raw Clinical Text
  │
  ├─ "Patient reports fatigue x 2 weeks. Denies fever."
  ├─ "BP 140/90, HR 88"
  ├─ "Type 2 Diabetes diagnosed 5 years ago"
  ├─ "Doctor: You have hypertension"
  └─ "Patient: I'm anxious about the upcoming surgery"
       │
       ▼
    Stage 1: Normalize to SOAP
       │
       ├─ Subjective: "Patient reports fatigue x 2 weeks. Denies fever. Anxious about surgery."
       ├─ Objective: "BP 140/90, HR 88"
       ├─ Assessment: "Type 2 Diabetes, Hypertension"
       └─ Plan: "Not documented"
            │
            ▼
    Stage 2: Generate Codes (from Assessment only)
       │
       ├─ Type 2 Diabetes → E11.9 (code it)
       ├─ Hypertension → I10 (code it)
       └─ Anxiety → NOT CODED (patient reported, not physician-confirmed)
            │
            ▼
    Evidence Extraction: Parse into Diagnosis objects
       │
       ├─ {condition: "Type 2 Diabetes", acuity: "chronic", ...}
       ├─ {condition: "Hypertension", ...}
       └─ Symptoms: ["fatigue", "anxiety"] (but anxiety won't be coded per gate)
            │
            ▼
    CodingResult Stored
       │
       ├─ soap_note: {subjective, objective, assessment, plan}
       ├─ icd_codes: [{code: E11.9, ...}, {code: I10, ...}]
       ├─ cpt_codes: []
       ├─ extracted_evidence: {diagnoses: [...], procedures: [], symptoms: [...]}
       └─ review_status: "pending"
```

---

## Key Decision Points in Pipeline

```
┌─────────────────────────────────────────┐
│ Is this diagnosis in ASSESSMENT?        │
│ (or just in Subjective/History?)        │
├─────────────────────────────────────────┤
│ NO → Do NOT code (patient history only) │
│ YES → Continue                          │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ Is it negated/uncertain?                │
│ (no, denies, ruled out, suspected)      │
├─────────────────────────────────────────┤
│ YES → Do NOT code                       │
│ NO → Continue                           │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ Is it a SYMPTOM or FINDING?             │
│ (R-codes, or general complaints)        │
├─────────────────────────────────────────┤
│ YES → Apply Symptom Coding Gate:        │
│    1. Integral to existing diagnosis?   │
│    2. Physician-confirmed separately?   │
│    3. Routine/expected?                 │
│    Code ONLY if ALL 3 = NO              │
│ NO (confirmed diagnosis) → Continue     │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ Select Code with MAX Specificity        │
│ (ICD-10: location, laterality, acuity) │
│ (CPT: approach, complexity, contrast)   │
├─────────────────────────────────────────┤
│ Assign confidence score (0.0–1.0)       │
│ with confidence_reason                  │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ Validate code against database          │
│ (CSV lookup)                            │
├─────────────────────────────────────────┤
│ Found → Accept                          │
│ Not found + format valid + high conf    │
│   → FLAG for review (new code?)         │
│ Invalid format → Try auto-correct       │
│   or FLAG if cannot correct             │
└─────────────────────────────────────────┘
```

---

## Current Limitations: Source Attribution Gap

### ❌ Problem: Source Information Lost

```
Stage 1 (Normalizes):
  Doctor: "What brings you in today?"
  Patient: "I've had anxiety for months"
  Doctor: "You have Type 2 Diabetes"
    │
    ▼
  SOAP:
  Subjective: "Patient reports anxiety"
  Assessment: "Type 2 Diabetes"
    │
    ▼ ← SOURCE INFORMATION LOST HERE!
    │
Stage 2 (Generates Codes):
  • "Patient reports anxiety" → Apply Symptom Gate → NOT coded (correct!)
  • "Type 2 Diabetes" → Code E11.9 (correct!)
    │
    BUT there's no explicit field saying:
    • "Diabetes" = physician_confirmed
    • "Anxiety" = patient_stated_only
    • This info exists in the LLM prompt but not in stored data
```

### ✅ Solution: Add Source Fields

```
Stage 1 Enhancement: Preserve Attribution
  SOAP + "attribution" section:
  {
    "assessment": "Type 2 Diabetes, Hypertension",
    "attribution": {
      "Type 2 Diabetes": "physician_confirmed",
      "Hypertension": "physician_confirmed"
    }
  }

Evidence Extraction Enhancement: Diagnosis with Source
  Diagnosis(
    condition="Type 2 Diabetes",
    source="physician_confirmed",  ← NEW
    is_current=True,               ← NEW
    source_evidence="...",         ← NEW
    confidence_in_source=0.95      ← NEW
  )

CodingResult Enhancement: Store Source Metadata
  extracted_diagnoses=[
    {
      "condition": "Type 2 Diabetes",
      "source": "physician_confirmed",
      "is_current": True,
      "coded_as": "E11.9"
    },
    {
      "condition": "Anxiety",
      "source": "patient_stated",
      "is_current": True,
      "coded_as": None,
      "not_coded_reason": "Patient reported but not physician-confirmed"
    }
  ]

Reviewer API Response: Show Source
  GET /api/coding/123/
  {
    "id": 123,
    "extracted_diagnoses": [
      {
        "condition": "Type 2 Diabetes",
        "source": "physician_confirmed",  ← Reviewer sees this
        "coded_as": "E11.9",
        "confidence": 0.95
      }
    ]
  }

ReviewFeedback: Track Source Errors
  POST /api/coding/123/review/
  {
    "feedback_type": "source_misidentified",  ← NEW TYPE
    "explanation": "Anxiety was actually physician-confirmed"
  }
```

---

## Summary: Where Source Information Is (& Isn't)

| Location | Currently? | Needed Enhancement |
|----------|-----------|-------------------|
| Raw clinical text | ✓ Doctor: ... Patient: ... | Extract source language explicitly |
| Stage 1 SOAP | ✗ SOAP only | Add 5th "attribution" dict or supplementary mapping |
| Stage 2 LLM prompt | ✓ Prompt checks "physician confirmed" | Already in Question 2 of Symptom Gate |
| Stage 2 Generated codes | ✗ Codes only, no source | Add "source" & "source_evidence" fields |
| Evidence Extraction | ✗ Diagnosis lacks source field | Add source, is_current, source_evidence fields |
| CodingResult model | ✗ No diagnosis source field | Add extracted_diagnoses JSONField |
| API Response | ✗ Source not exposed | Include diagnosis sources in serializer |
| ReviewFeedback | ✗ No source tracking | Add "source_misidentified" feedback type |

---

**Complete implementation instructions in: MEDICAL_CODING_PIPELINE_ARCHITECTURE.md**
