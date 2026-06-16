# Source Validation Quick Reference

**ICD-10-CM Rule (Section I.B.1):** _"Code only confirmed diagnoses. Never code patient-only statements."_

---

## Decision Table: What Gets Coded?

| **Who Said It?** | **What Type?** | **Code It?** | **Why** | **Code Type** |
|---|---|---|---|---|
| **Doctor** | Confirmed diagnosis this visit | ✅ YES | Physician confirms = billable | E11.9, F41.1, etc. |
| **Doctor** | Reviewing patient's past history | ⚠️ IF RELEVANT | Only if affecting current care | Z87.x (personal history) |
| **Patient** | Reported symptom (no doctor response) | ❌ NO | Patient-only statement ≠ physician diagnosis | — |
| **Patient** | Reported old injury/condition | ❌ NO | Patient-only history, unconfirmed | — |
| **Doctor** | "Possible/probable/rule out" | ❌ NO | Unconfirmed suspected diagnosis | — |
| **Doctor** | Historical problem, not addressed today | ❌ NO | Not active/relevant to today's care | — |

---

## Real Examples From Your Test Cases

### ❌ **Motorcycle Case** (CURRENTLY CODED INCORRECTLY)
```
Patient said:     "I injured my shoulder in June"
Doctor said:      [examines arm wounds, says "We'll clean and dress these"]
Current behavior: CODES S43.401A (shoulder injury) ← WRONG
Correct behavior: DO NOT code shoulder injury
Why:              Doctor never examined/confirmed shoulder
                  Patient-only statement, not physician-verified
```

### ❌ **Pheochromocytoma Case** (CURRENTLY CODED INCORRECTLY)
```
Patient said:     "I'm pretty anxious all the time"
Doctor said:      [no response about anxiety]
Current behavior: CODES F41.9 (anxiety disorder) ← WRONG
Correct behavior: DO NOT code F41.9
Why:              Doctor never said "you have anxiety disorder"
                  Patient self-reporting ≠ physician diagnosis

Patient said:     "I've lost 6kg without trying"
Doctor said:      [confirms pheo diagnosis, ordered workup]
Current behavior: CODES R63.4 (abnormal weight loss) ← WRONG
Correct behavior: DO NOT code R63.4 separately
Why:              Doctor attributed it to confirmed pheo (symptom of diagnosis)
                  Patient reported symptom, but doctor didn't diagnose it separately
```

### ✅ **Pneumonia Case** (SHOULD BE CODED CORRECTLY)
```
Patient said:     "I've had a cough for 10 days and fever"
Doctor said:      "You have pneumonia. I'll start antibiotics"
Correct behavior: CODE J18.9 (pneumonia)
                  DO NOT CODE R05.1 (fever) or R06.9 (cough)
Why:              Doctor confirmed diagnosis
                  Fever/cough are symptoms of confirmed pneumonia, not separate codes
```

---

## Source Validation Gate (Decision Tree)

```
STEP A: Who stated it?
├─ Only the patient → STOP, DO NOT CODE
├─ Doctor said/confirmed → Continue to Step B
└─ Doctor reviewing history → Continue to Step B

STEP B: What is the statement?
├─ Doctor diagnosed/confirmed this visit → Code it ✓
├─ Doctor mentioned past history (no current action) → Z87.x ONLY if affects care
├─ Doctor said "possible/rule out/probable" → Code symptom ONLY; NOT diagnosis
├─ Doctor ordered test (pending result) → Code the CPT; NOT the suspected diagnosis
└─ Doctor never responded to patient statement → DO NOT CODE

STEP C: Current vs historical?
├─ Being treated/managed TODAY → Use initial encounter code (7th char = A)
├─ Historical, not addressed today → Use Z87.x personal history (if relevant)
└─ Old injury from months/years ago → Use subsequent (D) or sequela (S), never (A)
```

---

## Files That Need Changes

| **File** | **Change Type** | **Why** | **Complexity** |
|---|---|---|---|
| [evidence_extractor.py](VirtualMedicalCoder/coding/evidence_extractor.py) | Add source fields to `Diagnosis` | Track who said what | Low |
| [models.py](VirtualMedicalCoder/coding/models.py) | Add `extracted_diagnoses` + `validation_log` fields | Store source metadata & decisions | Low |
| [two_stage_pipeline.py](VirtualMedicalCoder/nlp_engine/two_stage_pipeline.py) | Stage 1: Add attribution tagging; Stage 2: Add validation gate | Capture source; validate before coding | High |
| [code_retrieval.py](VirtualMedicalCoder/coding/code_retrieval.py) | Add `is_codeable_by_source()` function | Enforce gate in ranking logic | Medium |
| [serializers.py](VirtualMedicalCoder/coding/serializers.py) | Expose diagnosis sources in API | Reviewers see why each diagnosis coded/rejected | Low |
| [test_source_validation.py](test_source_validation.py) | Create new test file | Validate gate behavior on real cases | Medium |

---

## Impact Check: Your Current Test Cases

### Motorcycle Case
- **Current:** Codes S43.401A (shoulder) + S51.812A (arm cuts) with 7th char A
- **After fix:** Only codes S51.812A (what doctor treated); rejects S43.401A (unconfirmed patient history)
- **Status:** ⚠️ WILL CHANGE OUTPUT

### Pheochromocytoma Case  
- **Current:** Codes F41.9 (anxiety), D50.8 (anemia), R63.4 (weight loss) with high confidence
- **After fix:** Only codes the confirmed pheo + related diagnoses doctor explicitly confirmed
- **Status:** ⚠️ WILL CHANGE OUTPUT

### Pneumonia Case
- **Current:** Unknown; depends on how Stage 2 processes symptoms
- **After fix:** Should code J18.9 only; reject R05.9 + R06.9 as symptoms of confirmed diagnosis
- **Status:** ⚠️ LIKELY TO CHANGE OUTPUT

---

## Next Steps

1. **Read [SOURCE_VALIDATION_IMPLEMENTATION_PLAN.md](SOURCE_VALIDATION_IMPLEMENTATION_PLAN.md)** for detailed 5-phase implementation
2. **Phase 1:** Enhance data models (2-3 hours)
3. **Phase 2:** Update LLM prompts (4-6 hours, requires prompt engineering)
4. **Phase 3-4:** Integrate validation into pipeline (3-4 hours)
5. **Phase 5:** Test and iterate on real cases (4-6 hours)
6. **Total estimated effort:** 15-20 hours

---

## Compliance Verification

After implementation, audit with these checks:

- ✅ No diagnosis codes generated from patient-only statements
- ✅ All coded diagnoses have `source: "physician_confirmed"` or appropriate Z87.x
- ✅ Historical conditions use Z87.x instead of acute codes (7th char D/S, not A)
- ✅ API returns `source_evidence` field for every diagnosis
- ✅ Reviewers can see rejection reason for uncodeable diagnoses
- ✅ Test cases pass: [test_source_validation.py](test_source_validation.py)
