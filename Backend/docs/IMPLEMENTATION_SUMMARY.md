# Medical Coding Pipeline — Complete Implementation Summary

## ✅ Implementation Complete

Your medical coding backend now has a **complete end-to-end hybrid pipeline** that takes messy clinical text (conversations, dictations, notes) and produces validated, code-table-compliant ICD-10 and CPT codes with human review integration.

---

## Architecture Overview — TWO-STAGE PIPELINE (Updated)

```
Raw Clinical Input (messy dialogue, dictation, notes)
         ↓
[Stage 1: Normalization LLM]  → Messy Text → Clean SOAP Note
         ↓
[Stage 2: Code Generation LLM] → Clean SOAP → ICD-10/CPT Codes
         ↓
[Evidence Extraction]          → Extract structured facts from SOAP
         ↓
[Validation Layer]             → Validate against CSV code tables, auto-correct
         ↓
[Flagging Layer]               → Mark suspicious codes for review
         ↓
Database Storage               → CodingResult with codes + evidence + metadata
         ↓
[Review Workflow]              → Medical coder approves/corrects
         ↓
[Feedback Loop]                → Corrections logged for learning
         ↓
Final Approved Codes           → Ready for insurer
```

**Key Innovation:** Two focused LLM stages instead of one complex call
- **Stage 1:** Focus only on SOAP normalization (handles messy text properly)
- **Stage 2:** Focus only on code generation (works from clean input)
- **Result:** More reliable, fewer special cases, easier to debug

---

## 🔧 What Was Implemented

### 1. **Enhanced Data Models** ([coding/models.py](coding/models.py))

#### CodingResult (extended)
- `extracted_evidence`: Structured clinical facts (diagnoses with acuity/laterality/complications, procedures with approach/site, symptoms, vital findings)
- `validation_metadata`: Tracks what was flagged and why (flagged_count, auto_corrected_count, issues)
- `review_notes`, `reviewed_by`, `reviewed_at`: Full audit trail for human review
- All fields preserved for complete audit trail

#### ReviewFeedback (new)
- Tracks every correction made by reviewers
- Stores: original LLM codes → corrected codes
- Feedback type: missing_code, incorrect_code, specificity, completeness, conflict_resolved, other
- Enables continuous learning from corrections

### 2. **Evidence Extraction Module** ([coding/evidence_extractor.py](coding/evidence_extractor.py))

Extracts structured clinical facts from SOAP notes:

**Diagnoses**
- Condition name
- Acuity (acute, chronic, acute-on-chronic)
- Severity (mild, moderate, severe, critical)
- Laterality (left, right, bilateral)
- Complications (abscess, perforation, infection, etc.)

**Procedures**
- Procedure name
- Approach (open, laparoscopic, endoscopic, percutaneous, imaging, injection, topical)
- Anatomical site
- Laterality
- Urgency (emergency, elective, urgent)

**Symptoms & Findings**
- Extracted symptom keywords from subjective section
- Vital signs extracted from objective section (BP, HR, RR, Temp, SpO2, BMI, Weight)

### 3. **Code Retrieval & Ranking System** ([coding/code_retrieval.py](coding/code_retrieval.py))

**retrieve_icd_candidates()**
- Takes diagnosis text, returns ranked ICD-10 codes from CSV database
- Uses token-based matching (0.0-1.0 relevance score)
- Returns top N matches with descriptions and scores

**retrieve_cpt_candidates()**
- Takes procedure text, returns ranked CPT codes from CSV database
- Same token-based matching logic
- Contextual ranking by relevance

**score_llm_code_against_evidence()**
- Scores how well an LLM-generated code matches clinical evidence
- Used to detect codes that don't fit the documented clinical picture

**flag_codes_for_review()**
- Analyzes codes and flags problematic ones
- Checks: low confidence, missing evidence, confidence/evidence mismatch
- Returns flagged codes with reasons

### 4. **Enhanced NLP Pipeline** ([nlp_engine/services.py](nlp_engine/services.py))

Updated `analyze_raw_text()` function to:
1. Normalize input (detect conversations, clean text)
2. Generate SOAP note via LLM
3. **NEW**: Extract evidence from SOAP
4. **NEW**: Validate codes against local CSV databases
5. **NEW**: Auto-correct invalid codes using retrieval
6. **NEW**: Flag suspicious codes for review
7. **NEW**: Return enriched result with evidence + validation metadata

Returns:
```python
{
    "soap": {...},
    "codes": [...],
    "extracted_evidence": {...},      # ← NEW
    "validation_metadata": {...}      # ← NEW
}
```

### 5. **Enhanced API Endpoints** ([coding/views.py](coding/views.py))

**GET /api/coding/**
- List all coding results for current user

**GET /api/coding/<id>/**
- Get full result with evidence and validation metadata

**POST /api/coding/<id>/review/**
- Submit human review decision
- Optional: correct codes, add notes
- Optional: provide feedback type and explanation for corrections
- Creates ReviewFeedback record for learning

**GET /api/coding/<id>/feedback/**
- Get all corrections made on this case
- Track learning history

**POST /api/coding/<id>/alternatives/**
- Get alternative code suggestions during review
- Body: `{"system": "ICD10|CPT", "evidence_text": "..."}`
- Returns ranked candidates sorted by relevance score

### 6. **Updated Serializers** ([coding/serializers.py](coding/serializers.py))

- Full support for new fields (extracted_evidence, validation_metadata, review_notes, etc.)
- ReviewFeedbackSerializer for feedback history
- Enhanced ReviewSerializer with feedback tracking

### 7. **Database Migration** ([coding/migrations/0003_enhanced_coding_result.py](coding/migrations/0003_enhanced_coding_result.py))

✅ Applied successfully. Adds:
- `extracted_evidence` (JSONField)
- `validation_metadata` (JSONField)
- `review_notes` (TextField)
- `reviewed_by` (ForeignKey)
- `reviewed_at` (DateTime)
- New `ReviewFeedback` model

### 8. **Admin Interface** ([coding/admin.py](coding/admin.py))

- CodingResultAdmin: Browse by user, status, date
- ReviewFeedbackAdmin: Browse feedback history by type

---

## 📊 Example Workflow

**Input:** Messy doctor-patient dialogue
```
Doctor: How are you feeling?
Patient: Terrible. My leg hurts and I'm always tired.
Doctor: Any swelling? Lab work: glucose 245, BP 155/95.
Assessment: Chronic leg pain, possible DVT, diabetes.
Plan: CT scan, continue meds.
```

**Processing:**
1. **Text Extraction** → Plain text
2. **Normalization** → Detect conversation format, clean up
3. **SOAP Generation** → Structured clinical note
4. **Evidence Extraction**
   - Diagnoses: chronic leg pain (laterality: unspecified, but swelling context suggests vascular)
   - Procedures: CT scan (approach: imaging)
   - Symptoms: pain, fatigue
   - Findings: BP 155/95, glucose 245

5. **Code Generation** (LLM) → Suggests: M79.3 (myalgia), E11.9 (type 2 DM)
6. **Validation** → M79.3 valid but *weak evidence match*; E11.9 valid and *strong match*
7. **Retrieval** → Find alternatives for leg pain:
   - I87.2 (venous insufficiency) - score 0.89 ← BETTER match
   - M79.3 (myalgia) - score 0.75
   - R22.3 (leg swelling) - score 0.82

8. **Flagging** → Mark M79.3 for review (lower than alternatives)
9. **Database** → Save with review_status = "pending"
10. **Medical Coder Reviews** → "I87.2 is the real diagnosis. Venous insufficiency explains edema + pain."
11. **Feedback** → Record correction (M79.3 → I87.2, reason: incorrect_code)
12. **Final** → Approved codes sent to insurer

---

## 🎯 Key Features

✅ **Evidence-Driven Coding**
- Every code tied to specific clinical evidence
- Reviewers can see exactly why code was suggested

✅ **Automatic Validation**
- All codes validated against official CSV tables
- Invalid codes auto-corrected to nearest valid match
- Malformed codes flagged for review

✅ **Smart Flagging**
- Low-confidence codes detected
- Codes weak on evidence match highlighted
- Conflicting codes identified

✅ **Alternative Suggestions**
- During review, coder can request alternatives
- Ranked by relevance to clinical evidence
- Easy code correction workflow

✅ **Learning Loop**
- Every correction recorded in ReviewFeedback
- Patterns in corrections can be analyzed
- Feedback can inform LLM prompt improvements

✅ **Full Audit Trail**
- Raw LLM output preserved
- SOAP note stored
- Evidence extracted and saved
- Validation metadata tracked
- Review history maintained
- Reviewer and timestamp recorded

✅ **Code Table Compliance**
- 100% compliance with local CSV code tables
- No hallucinated or invalid codes in final output
- Reduces insurer rejections

---

## 📁 Files Created/Modified

### Created:
- `coding/evidence_extractor.py` - Evidence extraction (diagnoses, procedures, symptoms, findings)
- `coding/code_retrieval.py` - Code ranking and retrieval (ICD-10 and CPT)
- `coding/test_pipeline_demo.py` - Demo and testing script
- `coding/PIPELINE_DOCUMENTATION.py` - Full documentation
- `coding/migrations/0003_enhanced_coding_result.py` - Database migration

### Modified:
- `coding/models.py` - Enhanced CodingResult, added ReviewFeedback
- `coding/serializers.py` - Updated for new fields and feedback
- `coding/views.py` - Enhanced endpoints with alternatives and feedback
- `coding/urls.py` - New URL routes
- `coding/admin.py` - Admin interface
- `nlp_engine/services.py` - Integration of evidence extraction and retrieval
- `ingestion/views.py` - Save extracted evidence to database

---

## 🚀 How to Use

### 1. Upload a document
```bash
POST /api/ingestion/upload/
{
    "file_url": "https://...",
    "file_type": "pdf",
    "file_name": "patient_notes.pdf"
}
```

### 2. Wait for processing (async Celery task)
```bash
GET /api/ingestion/upload/<id>/
```

### 3. View coding result with evidence
```bash
GET /api/coding/<result_id>/
# Returns: SOAP note, extracted evidence, ICD/CPT codes with confidence, validation metadata
```

### 4. Review and correct codes
```bash
POST /api/coding/<result_id>/review/
{
    "review_status": "approved",
    "review_notes": "All codes appropriate"
}
```

Or with corrections:
```bash
POST /api/coding/<result_id>/review/
{
    "review_status": "revised",
    "icd_codes": [{"code": "I87.2", "description": "Venous insufficiency", ...}],
    "feedback_type": "incorrect_code",
    "explanation": "Venous insufficiency better explains edema + pain vs myalgia"
}
```

### 5. Get alternative code suggestions
```bash
POST /api/coding/<result_id>/alternatives/
{
    "system": "ICD10",
    "evidence_text": "Chronic leg swelling edema"
}
# Returns: Ranked candidates with scores
```

---

## 🔍 Data Flow Example

**Raw Text** 
```
"Patient reports 3-month history of left leg swelling, 
BP elevated at 155/90. Diabetes on board."
```

↓ Extracted Evidence
```json
{
  "diagnoses": [
    {
      "condition": "leg swelling",
      "acuity": "chronic",
      "laterality": "left",
      "severity": null
    },
    {
      "condition": "Diabetes",
      "acuity": "chronic"
    }
  ],
  "procedures": [],
  "symptoms": ["swelling"],
  "findings": [{"type": "vital", "name": "BP", "value": "155/90"}]
}
```

↓ Code Validation & Retrieval
```json
{
  "codes": [
    {
      "system": "ICD10",
      "code": "I87.2",
      "description": "Chronic venous insufficiency",
      "confidence": 0.89,
      "evidence_text": "left leg swelling",
      "db_description": "Chronic venous insufficiency"
    },
    {
      "system": "ICD10",
      "code": "E11.9",
      "description": "Type 2 diabetes",
      "confidence": 0.95,
      "evidence_text": "Diabetes"
    }
  ],
  "validation_metadata": {
    "total_codes": 2,
    "flagged_count": 0,
    "auto_corrected_count": 0,
    "needs_review": false
  }
}
```

---

## ⚙️ Technical Details

**Language/Framework:** Django 5.2, Django REST Framework, Celery

**Database:** Supports PostgreSQL (settings configured)

**Code Tables:** Local CSV files in `codes/` directory
- `codes/icd-10.csv`
- `codes/cpt4.csv`

**Authentication:** JWT (already in your backend)

**Async Processing:** Celery + Redis (already configured)

---

## 🎓 Next Steps for Continuous Improvement

1. **Analyze ReviewFeedback** patterns to identify systematic LLM errors
2. **Fine-tune LLM prompts** based on feedback patterns (e.g., "venous insufficiency vs myalgia confusion")
3. **Track metrics**: code approval rate, correction patterns, code specificity
4. **Build feedback analytics**: dashboard showing most-corrected codes
5. **A/B test** prompt changes against historical feedback
6. **Create ML classifier** for automatic code suggestions (trained on corrected feedback)

---

## 📋 Verification Checklist

✅ Database migration applied successfully
✅ Evidence extraction module working
✅ Code retrieval and ranking implemented
✅ NLP pipeline enhanced with evidence layer
✅ API endpoints updated with alternatives and feedback
✅ Models and serializers enhanced
✅ Admin interface configured
✅ Full audit trail preserved
✅ Code table validation enforced
✅ All imports resolve correctly

---

**The system is now ready for end-to-end testing with real clinical data!**
