"""
Medical Coding Pipeline Implementation — Complete System Architecture
=====================================================================

The system now implements a complete hybrid pipeline for medical coding:

Raw Clinical Text
       ↓
[Step 1] Text Extraction (PDF/Image/Audio → plain text)
       ↓
[Step 2] Normalization (conversation detection, cleanup)
       ↓
[Step 3] LLM Processing (generates SOAP + initial codes)
       ↓
[Step 4] Evidence Extraction (structured facts from SOAP)
       ↓
[Step 5] Code Validation & Retrieval (validate against CSVs, suggest alternatives)
       ↓
[Step 6] Flagging (mark problematic codes for review)
       ↓
CodingResult Database Model
       ├─ SOAP note (structured clinical summary)
       ├─ Extracted evidence (diagnoses, procedures, symptoms, findings)
       ├─ ICD-10 codes (with confidence, evidence text, validation flags)
       ├─ CPT codes (with confidence, evidence text, validation flags)
       ├─ Validation metadata (what was flagged and why)
       └─ Review status (pending → approved/rejected/revised)
       ↓
[Step 7] Human Review (medical coder approves/corrects)
       ↓
[Step 8] Feedback Tracking (corrections are logged for learning)
       ↓
Final Approved Codes → Sent to Insurer

==============================================================================
KEY COMPONENTS
==============================================================================

1. EVIDENCE EXTRACTION (coding/evidence_extractor.py)
   ─────────────────────────────────────────────────
   
   Extracts structured clinical facts from SOAP notes:
   
   - Diagnoses: condition name + acuity/laterality/complications/severity
   - Procedures: name + approach/site/laterality/urgency
   - Symptoms: reported complaints (fatigue, pain, etc.)
   - Findings: vitals (BP, HR, temp, SpO2, weight, BMI)
   
   Usage:
       from coding.evidence_extractor import EvidenceExtractor
       
       soap_note = {
           "subjective": "Patient reports chronic left-sided pain and fatigue",
           "objective": "BP 140/90, HR 78, temp 98.6F",
           "assessment": "Type 2 Diabetes, acute on chronic heart failure",
           "plan": "Continue metformin, order echocardiogram"
       }
       
       evidence = EvidenceExtractor.extract_evidence(soap_note)
       # Returns:
       # {
       #     "diagnoses": [
       #         {"condition": "Type 2 Diabetes", "acuity": "chronic", ...},
       #         {"condition": "heart failure", "acuity": "acute-on-chronic", ...}
       #     ],
       #     "procedures": [{"name": "echocardiogram", "approach": "imaging", ...}],
       #     "symptoms": ["pain", "fatigue"],
       #     "findings": [{"type": "vital", "name": "BP", "value": "140/90"}, ...]
       # }

2. CODE RETRIEVAL & RANKING (coding/code_retrieval.py)
   ────────────────────────────────────────────────────
   
   Retrieves candidate ICD-10 and CPT codes based on clinical evidence.
   Uses tokenized matching against local CSV code tables.
   Ranks by relevance score (0.0-1.0).
   
   Usage:
       from coding.code_retrieval import CodeRetriever
       
       # Get ICD-10 candidates for a diagnosis
       icd_candidates = CodeRetriever.retrieve_icd_candidates(
           "Type 2 Diabetes with complications",
           top_k=5,
           min_score=0.3
       )
       # Returns: [{"code": "E11.9", "description": "...", "score": 0.87}, ...]
       
       # Get CPT candidates for a procedure
       cpt_candidates = CodeRetriever.retrieve_cpt_candidates(
           "Echocardiogram transthoracic",
           top_k=5,
           min_score=0.3
       )
       # Returns: [{"code": "93000", "description": "...", "score": 0.92}, ...]
       
       # Score LLM-generated code against evidence
       score = CodeRetriever.score_llm_code_against_evidence(
           code_system="ICD10",
           code="E11.9",
           evidence_text="Type 2 diabetes"
       )
       # Returns: 0.85 (score how well it matches the evidence)

3. ENHANCED CODING RESULT MODEL
   ──────────────────────────────
   
   database schema in coding/models.py:
   
   class CodingResult(models.Model):
       # Identifiers
       upload_record (FK to UploadRecord)
       user (FK to User)
       
       # Core outputs
       soap_note (JSON)                    # {"subjective": "...", ...}
       extracted_evidence (JSON)           # {"diagnoses": [...], "procedures": [...], ...}
       icd_codes (JSON)                    # [{"code": "...", "confidence": 0.9, ...}]
       cpt_codes (JSON)                    # [{"code": "...", "confidence": 0.85, ...}]
       
       # Validation & Quality
       validation_metadata (JSON)          # {"flagged_count": 2, "issues": [...]}
       
       # Review workflow
       review_status (Choice)              # pending/approved/rejected/revised
       review_notes (Text)                 # Notes from reviewer
       reviewed_by (FK to User)            # Who reviewed
       reviewed_at (DateTime)              # When reviewed
       
       # Audit trail
       raw_llm_output (Text)               # Original LLM output
       created_at (DateTime)
       updated_at (DateTime)
   
   class ReviewFeedback(models.Model):
       # Tracks every reviewer correction
       coding_result (FK)
       reviewer (FK to User)
       llm_codes (JSON)                    # What LLM generated
       corrected_codes (JSON)              # What reviewer changed it to
       feedback_type (Choice)              # missing_code/incorrect_code/specificity/...
       explanation (Text)                  # Why the correction was made
       created_at (DateTime)

4. UPDATED NLP PIPELINE (nlp_engine/services.py)
   ─────────────────────────────────────────────
   
   The analyze_raw_text() function now:
   
   Step 1: Raw text → normalize/detect conversation → clean text
   Step 2: Send to LLM with enhanced system prompt
   Step 3: Parse LLM response → validate JSON format
   Step 4: Normalize SOAP note fields
   Step 5: Filter coding results (format validation)
   Step 6: ⭐ NEW: Extract evidence from SOAP
   Step 7: ⭐ NEW: Validate codes against CSV databases
   Step 8: ⭐ NEW: Auto-correct invalid codes using retrieval
   Step 9: ⭐ NEW: Flag codes needing review
   Step 10: Return enriched result with evidence + metadata
   
   Returns:
   {
       "soap": {...},
       "codes": [...],
       "extracted_evidence": {...},
       "validation_metadata": {...}
   }

5. API ENDPOINTS
   ──────────────
   
   GET /api/coding/
       List all coding results for current user
   
   GET /api/coding/<id>/
       Get details of one coding result with evidence
   
   POST /api/coding/<id>/review/
       Submit human review decision
       Body:
       {
           "review_status": "approved|rejected|revised",
           "icd_codes": [...],              # Optional correction
           "cpt_codes": [...],              # Optional correction
           "review_notes": "...",
           "feedback_type": "incorrect_code|specificity|...",
           "explanation": "Why I made changes..."
       }
   
   GET /api/coding/<id>/feedback/
       Get all review corrections for this case (learning history)
   
   POST /api/coding/<id>/alternatives/
       Get alternative code suggestions during review
       Body:
       {
           "system": "ICD10|CPT",
           "evidence_text": "..."
       }
       Returns: {"candidates": [{code, description, score}, ...]}

==============================================================================
EXAMPLE WORKFLOW
==============================================================================

SCENARIO: Patient with messy doctor-patient dialogue

Input (raw text):
───────────────
Doctor: Good morning, how are you feeling?
Patient: Terrible. My leg has been hurting for months. Also been tired all the time.
Doctor: Any swelling?
Patient: Yes, left leg is very swollen. I have diabetes too.
Exam shows elevated BP 155/95. Left leg edema, 2+ pitting. No acute wounds visible.
I'm going to order a CT to rule out DVT. Continue current meds.

Pipeline Execution:
──────────────────

1. TEXT EXTRACTION: Convert PDF/audio → plain text (above)

2. NLP PROCESSING:
   → Detects conversation format (Doctor/Patient)
   → Normalizes text
   → Generates SOAP:
     - Subjective: Patient reports left leg pain x months, fatigue, known diabetes
     - Objective: BP 155/95, left leg edema 2+ pitting, no wounds
     - Assessment: Chronic leg pain with swelling, edema, rule out DVT
     - Plan: CT imaging ordered, continue current medications

3. INITIAL CODE GENERATION (LLM):
   ICD-10: [M79.3, E11.9]  (leg pain, type 2 diabetes)
   CPT: [99214]             (office visit level 4)

4. EVIDENCE EXTRACTION:
   diagnoses:
     - "Chronic leg pain with swelling" (acuity: chronic, laterality: left)
     - "Type 2 diabetes" (acuity: chronic)
   procedures:
     - "CT imaging" (approach: imaging)
   symptoms:
     - pain (chronic, left leg)
     - fatigue (chronic)
   findings:
     - BP: 155/95 (elevated)
     - Edema: left leg, 2+ pitting

5. CODE VALIDATION & RETRIEVAL:
   For ICD M79.3: ✓ Valid, found in database
   For ICD E11.9: ✓ Valid, found in database
   For CPT 99214: ✓ Valid, found in database

6. EVIDENCE-BASED RANKING:
   Retrieve alternatives for "chronic leg pain left edema":
   - I87.2 "Venous insufficiency" (score: 0.89) ← might be better fit
   - M79.3 "Myalgia unspecified" (score: 0.75)
   - R22.3 "Swelling limb" (score: 0.82)
   
   → Flag M79.3 for review (lower score than alternatives)

7. FLAGGING FOR REVIEW:
   Validation Metadata:
   {
       "total_codes": 3,
       "flagged_count": 1,
       "auto_corrected_count": 0,
       "issues": [
           "ICD M79.3 has low evidence match (0.75) vs alternative I87.2 (0.89)"
       ]
   }

8. SAVED TO DATABASE:
   CodingResult created with review_status = "pending"
   Visible to medical coder with flagged codes highlighted

9. HUMAN REVIEW:
   Medical coder reviews:
   - "I87.2 is better here — patient has swelling/edema consistent with venous insufficiency"
   - POST /api/coding/<id>/review/
     {
         "review_status": "revised",
         "icd_codes": [{"code": "I87.2", ...}, {"code": "E11.9", ...}],
         "cpt_codes": [{"code": "99214", ...}],
         "feedback_type": "incorrect_code",
         "explanation": "Chronic venous insufficiency better explains bilateral edema + pain vs general myalgia"
     }

10. FEEDBACK RECORDED:
    ReviewFeedback:
    - llm_codes: [{code: M79.3}, ...]
    - corrected_codes: [{code: I87.2}, ...]
    - feedback_type: "incorrect_code"
    - explanation: "..."
    
    This feedback trains future improvements!

11. FINAL STATE:
    CodingResult.review_status = "revised"
    CodingResult.reviewed_by = <medical coder>
    Codes are now finalized and ready for insurer

==============================================================================
HOW TO USE
==============================================================================

1. UPLOAD A DOCUMENT:
   POST /api/ingestion/upload/
   {
       "file_url": "https://...",      (or)
       "file_type": "pdf|image|audio|raw_text",
       "raw_text": "..."               (if file_type = raw_text)
   }
   → Returns: {"id": 123, "status": "pending"}

2. POLL STATUS:
   GET /api/ingestion/upload/123/
   → Returns: {"status": "processing|completed|failed", ...}

3. RETRIEVE CODING RESULT:
   GET /api/coding/456/
   → Returns full result with extracted_evidence and validation_metadata

4. REVIEW AND CORRECT:
   POST /api/coding/456/review/
   → Submit your corrections and feedback

5. GET SUGGESTIONS:
   POST /api/coding/456/alternatives/
   {
       "system": "ICD10",
       "evidence_text": "..."
   }
   → See ranked alternative codes before you correct

==============================================================================
KEY DIFFERENCES FROM SIMPLE APPROACH
==============================================================================

Before (naive):
  Raw text → LLM → Codes → Save
  
  Problems:
  - No structured evidence for auditing
  - Can't validate codes against official tables
  - No flagging of questionable codes
  - Can't suggest alternatives during review
  - No learning loop from corrections

After (this implementation):
  Raw text → NLP → Evidence → Retrieval → Validation → Flagging → Review → Feedback
  
  Benefits:
  ✓ All codes tied to specific evidence
  ✓ Invalid/suspicious codes identified automatically
  ✓ Alternatives suggested based on evidence
  ✓ Reviewer corrections feed back into system
  ✓ 100% compliance with local code tables (CSVs)
  ✓ Lower rejection rate from insurers (verified codes)
  ✓ Continuous improvement through feedback

==============================================================================
"""

print(__doc__)
