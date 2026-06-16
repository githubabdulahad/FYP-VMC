# Source Validation Flow Diagrams

## Current Pipeline (INCORRECT - No Source Validation)

```
Raw Clinical Text
        ↓
    Stage 1
  (SOAP Gen) ← No attribution tagging - loses "who said it"
        ↓
Stage 1 Output
(Assessment only)
        ↓
    Stage 2
(Code Gen) ← No validation gate - codes everything in Assessment
        ↓
ICD-10/CPT Codes
(INCORRECT: includes patient-only statements ❌)
```

---

## Enhanced Pipeline (CORRECT - With Source Validation)

```
Raw Clinical Text
        ↓
    Stage 1
  (SOAP Gen)
        ├─ Tag: "[Doctor confirmed] Left leg fracture on X-ray"
        ├─ Tag: "[Patient reported] Patient said anxious all the time"
        └─ Tag: "[Doctor reviewed] History of shoulder surgery 2020"
        ↓
Stage 1 Output
(SOAP with source attribution)
        ↓
    Stage 2 - QUESTION 0
    (Source Validation Gate)
        ├─ Is it "[Doctor confirmed]"? 
        │  ├─ YES → Continue to coding ✓
        │  └─ NO → REJECT ❌
        ├─ Is it "[Patient reported]"?
        │  ├─ Only source → REJECT ❌
        │  └─ Confirmed by doctor → Continue ✓
        └─ Is it "[Doctor reviewed]"?
           ├─ Current visit, affects care → Use Z87.x ✓
           └─ Historical, no current action → REJECT ❌
        ↓
Stage 2 (Questions 1-5)
(Normal code ranking, but ONLY for accepted diagnoses)
        ↓
ICD-10/CPT Codes
(CORRECT: only physician-confirmed diagnoses ✓)
```

---

## Step 1: Stage 1 Enhancement (Attribution Tagging)

```
INPUT (Raw Text):
  Patient: "I injured my shoulder in June and I'm pretty anxious"
  Doctor: "Let me check your wounds. We'll clean and dress these"

CURRENT OUTPUT (Wrong):
  {
    "assessment": "Shoulder injury. Anxiety. Arm wounds",
    [No source info - Stage 2 will code everything]
  }

ENHANCED OUTPUT (Correct):
  {
    "assessment": "[Patient reported] Shoulder injury in June. 
                   [Patient reported] Patient said anxious all the time.
                   [Doctor confirmed] Arm wounds. Doctor will treat",
    [Source attribution preserved - Stage 2 can validate each]
  }
```

---

## Step 2: Stage 2 Enhancement (Validation Gate)

```
VALIDATION GATE PSEUDOCODE:

For each diagnosis in SOAP Assessment:
  
  1. Extract source attribution: "[Doctor confirmed]" vs "[Patient reported]" vs "[Historical]"
  
  2. GATE 1 - Source Validation:
     if source == "[Patient reported]":
         if NOT also confirmed by doctor:
             → REJECT (patient-only statement)
         else:
             → Accept (doctor also confirmed)
     else if source == "[Doctor confirmed]":
         → Accept for coding
     else if source == "[Historical]":
         → Check if affects current care
         → If yes: Use Z87.x code
         → If no: Reject
  
  3. JSON Output: Add source metadata
     {
       "condition": "Anxiety",
       "source": "patient_reported",
       "was_coded": false,
       "reason": "Patient statement without physician confirmation"
     }

EXAMPLE TRACE:

Diagnosis: "Shoulder injury"
Source tag: "[Patient reported]"
Doctor response: [None about shoulder]
Gate decision: REJECT ❌
Code output: [] (empty)
Validation log: "Source: patient_reported | Confirmation: none | Decision: REJECT | Rule: ICD-10-CM I.B.1"

---

Diagnosis: "Left arm lacerations"
Source tag: "[Doctor confirmed]"
Doctor statement: "Clean and dress these wounds"
Gate decision: ACCEPT ✓
Code output: [S51.812A, S51.812D] (etc.)
Validation log: "Source: physician_confirmed | Current visit: true | Decision: CODE"
```

---

## Step 3: Code Output Change (Diagnosis with Source Metadata)

```
CURRENT FORMAT (No source info):
{
  "icd_codes": [
    {"code": "S43.401A", "description": "...", "confidence": 0.9},
    {"code": "F41.9", "description": "...", "confidence": 0.85},
    {"code": "S51.812A", "description": "...", "confidence": 0.95}
  ]
}

ENHANCED FORMAT (With source validation):
{
  "extracted_diagnoses": [
    {
      "condition": "Shoulder injury",
      "icd_code": "S43.401A",
      "confidence": 0.9,
      "source": "patient_reported",
      "source_evidence": "Patient said 'I injured my shoulder in June'",
      "is_current_visit": false,
      "was_coded": false,  ← CHANGED BY SOURCE GATE
      "coding_decision": "REJECTED",
      "reason": "Patient statement without physician confirmation (ICD-10-CM I.B.1)",
      "validation_flag": "UNVERIFIED_PATIENT_STATEMENT"
    },
    {
      "condition": "Anxiety",
      "icd_code": "F41.9",
      "confidence": 0.85,
      "source": "patient_reported",
      "source_evidence": "Patient said 'I'm pretty anxious all the time'",
      "is_current_visit": false,
      "was_coded": false,  ← CHANGED BY SOURCE GATE
      "coding_decision": "REJECTED",
      "reason": "Patient statement without physician confirmation (ICD-10-CM I.B.1)",
      "validation_flag": "UNVERIFIED_PATIENT_STATEMENT"
    },
    {
      "condition": "Left arm lacerations",
      "icd_code": "S51.812A",
      "confidence": 0.95,
      "source": "physician_confirmed",
      "source_evidence": "Doctor: 'We'll clean and dress these wounds'",
      "is_current_visit": true,
      "was_coded": true,  ← NOT CHANGED - PASSES GATE
      "coding_decision": "APPROVED",
      "reason": "Physician confirmed at this visit"
    }
  ],
  "validation_summary": {
    "total_diagnoses_extracted": 3,
    "diagnoses_coded": 1,
    "diagnoses_rejected": 2,
    "rejection_breakdown": {
      "patient_statement_only": 2,
      "unconfirmed_suspected": 0,
      "historical_not_relevant": 0
    }
  }
}
```

---

## Test Case: Motorcycle Accident (Before & After)

### BEFORE (Current - WRONG)
```
Input: Patient injured shoulder; doctor treats arm wounds

Extracted diagnoses:
  ❌ S43.401A (shoulder injury) - confidence 0.92
  ✅ S51.812A (arm lacerations) - confidence 0.95
  
Output codes:
  Both coded

Validation issues:
  ❌ Shoulder injury coded despite being patient-reported,
    doctor never examined or confirmed it
```

### AFTER (Correct)
```
Input: Patient injured shoulder; doctor treats arm wounds

Extracted diagnoses with sources:
  ❌ REJECTED: S43.401A (patient reported, not confirmed)
  ✅ APPROVED: S51.812A (doctor confirmed, treating)
  
Output codes:
  Only arm lacerations coded

Validation log:
  "Shoulder: patient_reported → NO doctor confirmation → REJECT
   Arm: physician_confirmed → Active treatment today → CODE"

API response shows:
  coded_diagnoses: [S51.812A]
  rejected_diagnoses: [
    {
      condition: "Shoulder injury",
      reason: "Patient statement without physician confirmation",
      rule: "ICD-10-CM Section I.B.1"
    }
  ]
```

---

## Test Case: Pheochromocytoma (Before & After)

### BEFORE (Current - WRONG)
```
Input: Patient reports anxiety, weight loss; 
       Doctor confirms pheochromocytoma

Extracted diagnoses:
  ❌ F41.9 (anxiety) - confidence 0.85
  ❌ R63.4 (abnormal weight loss) - confidence 0.78
  ✅ E34.2 (pheochromocytoma) - confidence 0.94
  
All coded as separate diagnoses

Validation issues:
  ❌ Anxiety coded despite patient-reported, doctor never confirmed
  ❌ Weight loss coded as separate symptom (explains by pheo, not separate diagnosis)
  ✅ Pheo correctly coded
```

### AFTER (Correct)
```
Input: Patient reports anxiety, weight loss; 
       Doctor confirms pheochromocytoma

Extracted diagnoses with sources:
  ❌ REJECTED: F41.9 (patient said, doctor never diagnosed)
  ❌ REJECTED: R63.4 (symptom of confirmed pheo, not standalone diagnosis)
  ✅ APPROVED: E34.2 (physician confirmed)
  
Output codes:
  Only pheo coded

Validation log:
  "Anxiety: patient_reported → NO doctor confirmation → REJECT
   Weight loss: patient_reported + symptom of pheo → REJECT
   Pheo: physician_confirmed → Active diagnosis today → CODE"

API response shows:
  coded_diagnoses: [E34.2]
  rejected_diagnoses: [
    {condition: "Anxiety", reason: "Patient statement without physician confirmation"},
    {condition: "Abnormal weight loss", reason: "Symptom of confirmed diagnosis (pheo)"}
  ]
```

---

## Database Schema Change (CodingResult model)

```
CURRENT:
  icd_codes (JSON) = [{"code": "...", "confidence": ...}]
  No source info

ENHANCED:
  icd_codes (JSON) = [{"code": "...", "confidence": ..., 
                       "source": "physician_confirmed",
                       "was_coded": true/false}]
  
  extracted_diagnoses (JSON) = [
    {"condition": "...", "source": "...", "source_evidence": "...",
     "was_coded": true/false, "reason": "..."}
  ]
  
  validation_log (JSON) = {
    "summary": {...},
    "diagnoses_reviewed": [{...}]
  }
```

---

## Integration Points

```
Pipeline Flow:
  Raw text → Stage 1 (with attribution) → Stage 2 (with gate) → Code output
  
Review Workflow:
  API response includes source info
  → Reviewer sees which diagnoses passed gate and why
  → Feedback marks source_misidentified if gate was wrong
  
Training Loop:
  ReviewFeedback.source_misidentified
  → Helps refine Stage 1 attribution accuracy
  → Improves Stage 2 gate decision confidence
```

---

## Compliance Checklist

After implementation:

- [ ] Every diagnosis in output has `source` field
- [ ] Every diagnosis has `source_evidence` with supporting text
- [ ] Patient-only statements have `was_coded: false`
- [ ] No patient-reported diagnosis coded without physician confirmation
- [ ] Historical conditions use Z87.x instead of acute codes
- [ ] API exposes diagnosis sources to reviewers
- [ ] Test suite passes source validation scenarios
- [ ] Real test cases (motorcycle, pheo, pneumonia) produce correct outputs
