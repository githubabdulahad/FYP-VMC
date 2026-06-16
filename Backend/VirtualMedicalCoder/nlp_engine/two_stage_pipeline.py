"""
nlp_engine/two_stage_pipeline.py

Two-stage LLM pipeline for reliable medical coding:
  Stage 1: Raw messy text → Clean structured SOAP
  Stage 2: Clean SOAP → Accurate ICD-10/CPT codes

This is simpler and more reliable than complex parsing logic.
"""

import json
import os
import re
from typing import Any

import requests

try:
    import ollama
except ImportError:
    ollama = None


# ============================================================================
# STAGE 1: TEXT NORMALIZATION PROMPT
# ============================================================================
STAGE_1_NORMALIZE_PROMPT = """You are a medical documentation specialist. Your ONLY task is to convert messy clinical text into a clean, structured SOAP note format.

INPUT: Raw clinical text (conversation, dictation, fragmented notes, etc.)
OUTPUT: Clean structured SOAP note in JSON format ONLY

Rules:
1. Extract clinical information ONLY - ignore greetings, pleasantries, meta-discussion
2. Preserve ALL clinical findings exactly as documented
3. Group information into SOAP sections logically
4. For ASSESSMENT section:
   - If explicit diagnoses/impressions exist, extract them verbatim
   - If NO explicit assessment but clinical findings exist in Subjective/Objective:
     * DO NOT write "Not documented" 
     * INFER a clinical assessment from the documented symptoms and findings
     * Example: If objective shows "swelling and pain on left leg" → assessment should be "Left leg swelling and pain" or similar
   - Always try to generate SOMETHING meaningful from the clinical data
5. CRITICAL - ATTRIBUTION TAGGING FOR SOURCE VALIDATION (NEW - ICD-10-CM I.B.1 compliance):
   When extracting diagnoses and symptoms, tag who stated/confirmed them in the Assessment:
   - "[Doctor confirmed]" = Doctor explicitly stated, diagnosed, examined, or treated this condition
   - "[Patient reported]" = Patient stated this condition without doctor confirming it
   - "[Doctor reviewed]" = Doctor mentioned this as part of patient's history but not actively treating/confirming today
   
   Examples of attribution tagging in Assessment:
   ✓ "[Doctor confirmed] Left leg lacerations. Doctor will clean and dress wounds"
   ✓ "[Patient reported] Patient said 'I injured my shoulder in June'"
   ✓ "[Patient reported] Anxiety - patient stated 'I'm anxious all the time'"
   ✓ "[Doctor reviewed] History of appendectomy 2020"
   
   These tags help Stage 2 determine what can be coded (physician-confirmed only) and what cannot (patient-reported only).
6. VISIT TYPE INDICATOR (applies to ALL visit types - trauma, chronic disease, acute, etc.):
   - If clinical text contains FIRST-VISIT language: "What brings you in today?", "I haven't seen you before", 
     "initial evaluation", "referred by", "new patient", "first time", "initial visit"
     → Add to Assessment or Plan: "[Initial visit]" or "[New patient]" so Stage 2 can identify it
   - If clinical text contains FOLLOW-UP language: "Follow-up visit", "established patient", "seen before", 
     "ongoing care", "return visit"
     → Add to Assessment or Plan: "[Follow-up visit]" or "[Established patient]"
     - This indicator helps Stage 2 select correct E/M codes (99202-99205 for new vs 99212-99215 for established)
7. Return ONLY valid JSON, no markdown, no text before/after

SOAP Format:
{
  "subjective": "Patient-reported symptoms, complaints, history (what patient says)",
  "objective": "Findings from examination, vitals, labs, imaging, test results (measurable data)",
  "assessment": "Clinical diagnoses and impression (always try to infer from subjective/objective)",
  "plan": "Treatments, medications, procedures, follow-up (what will be done)"
}

Input text:
"""

# ============================================================================
# STAGE 2: CODE GENERATION PROMPT (Enhanced)
# ============================================================================
STAGE_2_CODE_GENERATION_PROMPT = """You are a certified medical coding specialist. Your task is to generate accurate ICD-10 and CPT codes from a clean SOAP note.

INPUT: Structured SOAP note (already clean and organized)
OUTPUT: ICD-10 and CPT codes in JSON format ONLY

CRITICAL RULES - READ CAREFULLY:

[SOURCE VALIDATION GATE - QUESTION 0 - APPLY BEFORE CODING ANY DIAGNOSIS]
This is the FIRST gate every diagnosis must pass (ICD-10-CM Section I.B.1):

Rule: "Code only confirmed diagnoses. Never code patient-only statements."

For EACH diagnosis mentioned in the Assessment (after Stage 1 attribution tagging), apply this gate:

STEP A: Who stated it? (Check the attribution tag from Stage 1)
  - "[Doctor confirmed]" → Continue to Step B ✓
  - "[Patient reported]" → Check Step B before coding
  - "[Doctor reviewed]" → Check Step B before coding
  - No tag (assume physician-confirmed in Assessment) → Continue to Step B ✓

STEP B: Is physician confirmation present?
  - If tag is "[Doctor confirmed]" AND doctor is actively treating/confirming → YES, code it ✓
  - If tag is "[Patient reported]" AND doctor never mentioned/confirmed → NO, reject it ❌
  - If tag is "[Doctor reviewed]" AND not actively treating today → NO, reject it ❌ (only use Z87.x if affects current care)
  - If doctor said "possible", "probable", "rule out", "suspected" → NO, reject it ❌

STEP C: Is it current or historical?
  - If Assessment says doctor is treating/managing THIS VISIT → YES, code with 7th char 'A' ✓
  - If Assessment mentions past history (not treated today) → NO, don't code ❌ (or use Z87.x if relevant)
  - If diagnosed months/years ago and not active today → NO, don't code ❌

OUTPUT: For each diagnosis, include in JSON:
  "source": "physician_confirmed" | "patient_reported" | "historical" | "unconfirmed_suspected"
  "was_coded": true | false
  "coding_decision": "APPROVED" | "REJECTED"
  "reason": "Explains why diagnosis was coded or rejected"
  "validation_rule": "ICD-10-CM Section I.B.1" or applicable rule

EXAMPLES FROM YOUR TEST CASES:

Diagnosis: "Shoulder injury" — Patient said "I injured my shoulder in June"
→ Source: "[Patient reported]"
→ Doctor response: Doctor never examined or mentioned shoulder
→ Gate Decision: REJECTED ❌
→ Reason: "Patient statement without physician confirmation (ICD-10-CM I.B.1)"
→ Coding: Do NOT code S43.401A

Diagnosis: "Anxiety" — Patient said "I'm anxious all the time"
→ Source: "[Patient reported]"
→ Doctor response: Doctor never diagnosed or treated anxiety
→ Gate Decision: REJECTED ❌
→ Reason: "Patient statement without physician confirmation (ICD-10-CM I.B.1)"
→ Coding: Do NOT code F41.9

Diagnosis: "Left arm lacerations" — Doctor said "We'll clean and dress these wounds"
→ Source: "[Doctor confirmed]"
→ Doctor action: Doctor is treating TODAY
→ Gate Decision: APPROVED ✓
→ Reason: "Physician confirmed and actively treating at this visit"
→ Coding: CODE S51.812A (with appropriate 7th char A for initial)

Diagnosis: "Type 2 Diabetes" — Doctor says "Patient has Type 2 Diabetes on metformin"
→ Source: "[Doctor confirmed]"
→ Doctor action: Doctor is managing TODAY
→ Gate Decision: APPROVED ✓
→ Reason: "Physician confirmed at this visit"
→ Coding: CODE E11.9 (or more specific code if complications documented)

[EVIDENCE-CODE MATCHING - ABSOLUTELY CRITICAL]
Each code MUST have evidence_text that DIRECTLY supports it:
- WRONG: code S81.812A (left leg) with evidence "Deep cuts on the right arm" ❌
- RIGHT: code S81.812A (left leg) with evidence "Left leg swelling and pain" ✓
- Each code gets its own matching evidence from the SOAP
- Do NOT reuse evidence from other codes
- Do NOT put evidence for wrong body part

[MATCHING ACCURACY - MOST IMPORTANT]
1. ONLY code what is EXPLICITLY documented in the Assessment
2. Match anatomical sites EXACTLY:
   - If assessment says "left leg", code LEFT leg injuries, NEVER right
   - If assessment says "right arm", code RIGHT arm injuries, NEVER thigh/hip
   - If assessment says "shoulder", code SHOULDER, NEVER spine
3. Match laterality precisely:
   - left = typically S code with 1 or 9 in 5th/6th position
   - right = typically S code with 0 or 9 in 5th/6th position
4. If uncertain about exact site or laterality, use lower specificity and confidence < 0.85

[ICD-10 CHAPTER SELECTION - CRITICAL FOR ACCURACY]
Choose the CORRECT S-code chapter based on INJURY TYPE documented:
- Swelling, pain, bruising, edema (NO visible break): S80.xxx (contusion/injury) NOT S81 (open wound)
- Laceration, cut, tear, bleeding wound: S81.xxx (open wound)
- Strain, sprain, ligament tear: S43.xxx, S63.xxx, etc.
- Fracture: S12.xxx, S32.xxx, S52.xxx, S82.xxx (explicit fracture codes)
If assessment says "left leg swelling and pain" → S80.9xxA NOT S81.8xxA
If assessment says "deep cuts on arm" → S51.8xxA (open wound) ✓

[ICD-10 7TH CHARACTER TIMING RULES - ABSOLUTELY CRITICAL]
The 7th character DEPENDS on when injury occurred and timing:
- 'A' = initial encounter (fresh injury being treated NOW)
- 'D' = subsequent encounter (follow-up, routine check of ongoing issue)
- 'S' = sequela (late effect, old injury causing current symptoms)

For HISTORICAL injuries (documented but from months/years ago, not currently treated):
- If mentioned as "previous injury" or dated to past month/year: use 'D' not 'A'
- Example: "History of shoulder injury from June 2025" → S43.4xxD (subsequent), NOT S43.4xxA
- Only use 'A' for injuries being treated today

For CURRENT injuries (documented as active, being treated):
- Use 'A' (initial encounter)

[EXTERNAL CAUSE CODES - MAXIMUM SPECIFICITY REQUIRED]
V/W/X/Y codes MUST match the specific accident type:
- V23.4XXA = motorcycle rider hit by PICK-UP TRUCK or VAN specifically
- V23.9XXA = motorcycle rider hit by UNSPECIFIED motor vehicle
- If accident says "car pulled out" → V23.9XXA (unspecified), NOT V23.4XXA
- V01.9XXA = pedestrian hit by unspecified vehicle
- Only use specific V2x.4/V2x.0 if that exact vehicle type documented

[PLACE OF OCCURRENCE CODES - EXACT LOCATION MATCHING]
Y92 codes MUST match the actual location:
- Y92.410 = street and highway (road accident location)
- Y92.411 = interstate highway
- Y92.830 = public park (NOT street/highway)
- If location says "roadway" or "highway" → Y92.410 or Y92.411
- If location says "park" → Y92.830
- Match location exactly; do not confuse park with road

[ICD-10 DIAGNOSIS CODES - ALL TYPES]

TYPE 1: ACUTE/CURRENT INJURIES (S-codes)
For each acute injury/condition documented in Assessment:
- Use MAXIMUM specificity FROM SOAP (laterality, severity, type, site)
- Match body parts exactly as documented
- Use 7th character 'A' for current, active treatment
- Example: "Left leg swelling" → S80.9xxA with left codes

TYPE 2: HISTORICAL/PREVIOUS INJURIES (S-codes)
If Assessment mentions previous injuries (shoulder, lower back, neck strain, etc.):
- Code these too with appropriate injury codes
- Use confidence 0.75-0.85 (since they're historical)
- Use 7th character 'D' (subsequent) for historical injuries, NOT 'A'
- Example: "History of shoulder injury" → S43.4xxD with lower confidence

TYPE 3: EXTERNAL CAUSE CODES (V/W/X/Y codes) - REQUIRED FOR TRAUMA
For each trauma/accident mentioned:
- Include V/W/X/Y codes with MAXIMUM specificity based on documented details
- Verify vehicle type matches (car vs truck vs unspecified)
- Include specific vehicle codes ONLY if that exact vehicle type documented
- These are REQUIRED for trauma cases, do not omit

TYPE 4: PLACE OF OCCURRENCE CODES (Y92 codes)
If specific location mentioned:
- Include Y92 code for place with exact location match
- Verify code description matches actual location (street ≠ park)
- Only if location explicitly stated

[ACUITY ESCALATION RULE - CRITICAL - PREVENTS OVERCODING]
NEVER assign a higher-acuity/higher-severity ICD-10 subcode unless the note explicitly contains escalation language.

Common mistake: Symptoms alone do NOT justify acuity escalation.

Examples of what NOT to do:
- Note says: "Patient presents with shortness of breath" (no word "exacerbation")
  → Do NOT code J44.1 (COPD with acute exacerbation)
  → Code J44.9 (COPD, unspecified) instead
  → Reason: SOB alone ≠ exacerbation; exacerbation requires explicit language

- Note says: "Chest pain in ER" (no word "infarction" or "MI")
  → Do NOT code I21.x (ST-elevation or non-STEMI)
  → Code R07.x (chest pain) or I10 (hypertension, if that's the context)
  → Reason: Chest pain alone ≠ MI; MI requires explicit diagnosis

- Note says: "Patient confused" (no word "encephalopathy" or "delirium")
  → Do NOT code G89.29 (pain, unspecified)
  → Investigate what the actual documented diagnosis is
  → Reason: Symptoms ≠ diagnosis; always code what IS documented

COPD-specific examples:
  "COPD presents with shortness of breath" → J44.9 (unspecified)
  "COPD with acute exacerbation" → J44.1 (with acute exacerbation)
  "COPD with acute bronchitis" → J44.0 (with acute lower respiratory infection)
  "COPD with acute asthma-like exacerbation" → J44.1

Diabetes-specific examples:
  "Type 2 diabetes" with no other detail → E11.9 (without complications)
  "Type 2 diabetes with hyperglycemia, HbA1c 8.2%" → E11.65 (with hyperglycemia)
  "Type 2 diabetes with neuropathy" → E11.40 (with diabetic neuropathy)

Rule: Match ICD-10 subcode to what is EXPLICITLY DOCUMENTED in Assessment, not to inferred severity.

TYPE 5: CHRONIC CONDITIONS & DIAGNOSES (E, I, J, M codes, etc.)
For non-trauma diagnoses documented in Assessment:
- E-codes: Type 2 diabetes (E11.x), Type 1 diabetes (E10.x)
- I-codes: Hypertension (I10), Heart disease (I25, I50), etc.
- J-codes: Asthma (J45), COPD (J44), Pneumonia (J18), etc.
- Z-codes: Obesity (E66), Hyperlipidemia (E78), etc.
- Use specificity indicators: .65 for hyperglycemia, .9xxA for initial, D for subsequent
- Example: "Type 2 diabetes mellitus without complications — HbA1c 7.4%" → E11.65 (with hyperglycemia)
- Example: "Essential hypertension — blood pressure slightly elevated" → I10
- Match severity/control indicators in Assessment to code specificity

[STAGE-SPECIFIC ICD-10 CODES - CRITICAL FOR ACCURACY]
Some diagnoses require stage/severity specification in the 5th character position:

CHRONIC KIDNEY DISEASE (N18.x) - MUST MATCH STAGE EXACTLY:
Assessment says "CKD, stage 3a" → code N18.31 (stage 3a), NOT N18.3 (unspecified)
Assessment says "CKD, stage 3b" → code N18.32 (stage 3b), NOT N18.3
Assessment says "CKD, stage 1" → code N18.1
Assessment says "CKD, stage 2" → code N18.2
Assessment says "CKD, stage 4" → code N18.4
Assessment says "CKD, stage 5" → code N18.5
Assessment says "CKD, stage 3" (no substage) → code N18.3 (unspecified stage 3)

KEY RULE: If stage/substage is EXPLICITLY DOCUMENTED (3a, 3b, etc.), ALWAYS use that specificity
Do NOT default to generic N18.3 when clinical text specifies 3a or 3b

[MANIFESTATION CODE REQUIREMENTS - ICD-10 INSTRUCTIONAL CODES]
Some ICD-10 codes REQUIRE secondary codes to fully describe the condition:

N40.1 (Benign prostatic hyperplasia with lower urinary tract symptoms):
  MANDATORY SECONDARY CODES:
  - If assessment mentions "nocturia" → MUST also code R35.1 (Nocturia)
  - If assessment mentions "urinary frequency" → MUST also code R35.0 (Urinary frequency)
  - Rationale: ICD-10 coding guideline requires separate symptom codes with N40.1

Example:
  Assessment: "Benign prostatic hyperplasia with lower urinary tract symptoms (LUTS) — mildly progressed.
               Reports moderate urinary frequency and nocturia"
  → Code: N40.1 (BPH with LUTS)
  → Code: R35.0 (Urinary frequency) — mandatory secondary code
  → Code: R35.1 (Nocturia) — mandatory secondary code

[SECONDARY HYPERTENSION FROM ENDOCRINE CONDITIONS - CRITICAL]
If Assessment documents an endocrine condition CAUSING hypertension (not just hypertension + endocrine):
- Pheochromocytoma causing hypertension → I15.2 (hypertension secondary to endocrine disorders)
  NOT I10 (essential hypertension)
- Thyroid disease causing hypertension → I15.2
- Cushing's syndrome causing hypertension → I15.2

Key distinction:
  I10 = Essential hypertension (no known secondary cause)
  I15.x = Secondary hypertension (documented cause identified)
  
If Assessment says "Pheochromocytoma causing hypertension" → code BOTH:
  E27.5 (pheochromocytoma)
  I15.2 (secondary hypertension FROM the pheochromocytoma)
  NOT I10 (which implies no known cause)

[DANGEROUS MISCODING PREVENTION - CRITICAL FOR SAFETY]
These specific miscodings have caused clinical harm. NEVER code these:

1. Visual disturbances during hypertensive crisis ≠ Hallucinations
   Patient symptom: "Purple-ish vision" during BP spike
   ❌ NEVER → R44.3 (hallucinations, other)
   → Use H53.9 (visual disturbance, unspecified) OR do not code if integral to hypertensive crisis
   → Hallucination codes imply psychiatric/neurological condition — DO NOT MISUSE

2. Chemotherapy ≠ Surgery
   Patient planning: Scheduled for adrenalectomy (surgical removal)
   ❌ NEVER → Z51.11 (encounter for antineoplastic chemotherapy)
   → Z51.11 is for active chemotherapy sessions, never for surgical planning
   → Surgery is a different procedure, coded with CPT when performed, not with Z51 codes

[SYMPTOM CODING DECISION GATE - CRITICAL - MUST FOLLOW BEFORE CODING ANY R-CODE OR F-CODE SYMPTOM]

BEFORE assigning ANY symptom code (R00-R99, F-codes for anxiety/mental status, etc.), 
answer these three questions IN ORDER. If ANY answer is YES → do NOT code that symptom.

QUESTION 1: Is this symptom INTEGRAL to a confirmed diagnosis already being coded?
  Examples:
    - Cough + fever with pneumonia diagnosis → cough/fever are integral, do NOT code R05.1 or R50.9
    - Tachycardia + palpitations with pheochromocytoma → integral symptoms, do NOT code R00.0
    - Sweating with pheochromocytoma → integral symptom, do NOT code R61
    - Headache with pheochromocytoma → integral symptom, do NOT code R51.9
    - Elevated BP reading (R03.0) when hypertension already diagnosed → R03.0 is the reading, not a separate diagnosis
  → YES (symptom is integral) = do NOT code

QUESTION 2: Did the PHYSICIAN explicitly diagnose/confirm this as a separate diagnosis, 
  or did only the PATIENT report it without physician confirmation?
  Examples:
    - Patient reports anxiety but physician never states "I diagnose you with anxiety disorder" → do NOT code F41.9
    - Patient says "I'm tired" but no physician assessment of fatigue or anemia → do NOT code R53.1
    - Patient mentions "dizziness" but no physician observation or diagnosis → do NOT code R42
  Physician-confirmed examples:
    - Doctor: "You have diabetic neuropathy" → code it
    - Doctor: "Your exam shows focal neurological deficit" → code it
  → NO physician confirmation = do NOT code

QUESTION 3: Is there a confirmed diagnosis already coded that makes this finding EXPECTED/ROUTINE?
  Examples:
    - Hypertensive crisis documented → elevated BP (R03.0) is routine/expected, do NOT code separately
    - Septic shock diagnosed → tachycardia is routine, do NOT code R00.0
    - Acute anxiety attack diagnosed → tachycardia is routine, do NOT code R00.0
  → YES (finding is routine for the diagnosis) = do NOT code

SPECIAL RULES - Never assign these codes even if symptoms present:
- R44.x (Hallucinations) for visual disturbances during hypertensive episodes
  → Visual disturbance during crisis = NOT hallucinations, use H53.9 or do not code
- R03.0 (Elevated BP reading) when hypertension/secondary HTN already coded
  → R03.0 is mutually exclusive with HTN diagnosis codes
- Z51.11 (Chemotherapy encounter) for surgical planning
  → Surgery is surgical procedure, never confuse with chemotherapy
- Z79.x (Long-term medication use) for newly prescribed drugs at this visit
  → Only for medications patient was already taking, not newly started drugs

DECISION RULE: Only code a symptom if ALL THREE of these answers are NO:
  Q1 = NO (symptom is NOT integral to a diagnosis)
  Q2 = NO (physician DID explicitly confirm it separately)
  Q3 = NO (it is NOT a routine/expected finding for existing diagnoses)

Symptom codes are valid ONLY in rare cases where symptoms don't fit any confirmed diagnosis.
Example: Patient with unknown cause headache → R51.9 OK (investigating)
Not valid: Headache with migraine diagnosis → headache is integral, do NOT code R51.9

[SYMPTOM CODING EXAMPLES - PHEOCHROMOCYTOMA CASE]
For reference (this case has pheochromocytoma diagnosis):
- Purple-ish vision during episode: Integral symptom of pheo crisis, do NOT code
  If must code: H53.9 (visual disturbance) only if NOT part of pheo diagnosis
- Tachycardia/palpitations: Integral symptoms of pheo, do NOT code R00.0
- Diaphoresis/sweating: Integral symptom of pheo triad, do NOT code R61
- Headache: Integral symptom of pheo triad, do NOT code R51.9
- High BP reading: Routine for pheo/HTN diagnosis, do NOT code R03.0
- Patient-reported anxiety: NOT physician-confirmed diagnosis, do NOT code F41.9

TYPE 6: STATUS/FACTOR CODES (Z-codes)
For medications, procedures, and status documented in Plan/Assessment:
IMPORTANT: Only include Z-codes that exist in official ICD-10 database. Do NOT invent medication codes.

AVAILABLE MEDICATION Z-CODES (verified in database):
- Z79.4 = long-term use of insulin (if insulin therapy documented)
- Z79.2 = long-term use of antibiotics (if antibiotic therapy documented)
- Z79.82 = long-term use of aspirin (if aspirin documented)
- Z79.83 = long-term use of bisphosphonates (if bisphosphonate therapy documented)
- Z79.84 = long-term use of oral hypoglycemic (if metformin, sulfonylurea documented)
- Z79.891 = long-term use of opiate analgesic (if opioid pain medication documented)
- Z79.899 = other long-term drug therapy (ONLY if specific medication name/class documented, NOT speculative)

STATUS/CONDITION Z-CODES:
- Z09 = follow-up examination AFTER COMPLETED TREATMENT ONLY
  ✓ Use Z09 ONLY if: Patient returns for check-up AFTER finishing treatment/intervention
  ✓ Example: "Patient returns for follow-up after pneumonia treatment completed" → Z09
  ❌ Do NOT use Z09 for: Established patients with ongoing chronic disease management
  ❌ Example: "Patient with COPD presents with shortness of breath" → NO Z09 (this is ongoing management, not post-treatment)
  ❌ Example: "Diabetic patient returns for routine diabetes management" → NO Z09 (this is chronic disease management)
  Key distinction: "Established patient" ≠ "Post-treatment follow-up"
  - Established patient visit = patient was seen before, ongoing care
  - Post-treatment follow-up = patient completing/completed a treatment course
  
- Z12.x = screening for condition (if screening documented)

EXAMPLES:
- Plan says "Continue insulin" → include Z79.4
- Plan says "Started on metformin" → include Z79.84
- Plan says "Taking aspirin" → include Z79.82
- Plan says "Prescribe opioid" → include Z79.891
- Follow-up visit → include Z09

CRITICAL Z79.899 RESTRICTION:
Z79.899 should ONLY be used when:
  1. The specific medication or drug class is NAMED in the assessment/plan
  2. The medication is ALREADY being taken (not newly prescribed)
  3. It is NOT one of the specific Z79.x codes (Z79.4, Z79.2, Z79.82, Z79.84, Z79.891, etc.)

DO NOT code Z79.899 if:
  ❌ Only vague references like "renal protection strategies" (no specific drugs named)
  ❌ Only directive language like "continue current medications" (no names listed)
  ❌ Newly prescribed drugs at this visit (only if already taking them long-term)

CORRECT EXAMPLE: "Continue ACE inhibitors for renal protection" → specific drug class named → Z79.899 acceptable
INCORRECT EXAMPLE: "Continue current renal protection strategies" → too vague, no drug named → do NOT code Z79.899

Important: Do NOT generate Z79.01, Z79.02 for antihypertensives or beta blockers
(these codes do not exist for those medication classes in the database). 
Only generate medications from the AVAILABLE list above.

TYPE 7: CPT EVALUATION & MANAGEMENT (E/M) CODES
For office visits and patient encounters:

[NEW vs ESTABLISHED PATIENT DETECTION - CRITICAL]
Determine patient status FIRST to select correct code range:
- NEW PATIENT (99202-99205): No prior documented relationship with provider
  Signals: "referred by", "first visit", "new patient", "initial evaluation", no prior visit mentioned
  Complexity: 99202=straightforward, 99203=low, 99204=moderate, 99205=high
- ESTABLISHED PATIENT (99212-99215): Prior visit with same provider documented
  Signals: "follow-up", "established patient", "seen before", "continuing care"
  Complexity: 99212=minimal, 99213=low-mod, 99214=moderate, 99215=high
- When unclear → default to NEW PATIENT codes and flag for review

[COMPLEXITY DETERMINATION]
Assess medical decision-making (MDM) based on:
- Chief complaint severity (acute/complex vs routine)
- Exam scope (focused vs comprehensive)
- Physical exam findings (abnormal findings increase complexity)
- Number of diagnoses (1 simple = low, 2-3 = moderate, 3+ complex = high)
- Procedures/imaging ordered (increases complexity)

Examples:
- Acute pneumonia with chest X-ray → NEW 99203 (new patient, moderate MDM)
- Chronic disease follow-up with medication increase → ESTABLISHED 99214
- Established patient brief check-in → ESTABLISHED 99212-99213

[CODING RULES]
- Do NOT use 99211 (no provider exam) unless documentation explicitly states only nursing visit
- Do NOT include if only phone/telehealth (use 99441-99443 instead)
- Include confidence 0.85-0.95 if office visit clearly documented

TYPE 8: CPT LAB & DIAGNOSTIC PROCEDURE CODES
For lab tests and diagnostic procedures documented in Objective findings or ordered in Plan:

COMMON LAB CODES:
- 83036 = Hemoglobin A1C (HbA1c result documented)
- 82947 = Fasting glucose (fasting glucose result documented)
- 80053 = Comprehensive metabolic panel (if multiple metabolic values documented)
- 85025 = Complete blood count (CBC)
- 80061 = Lipid panel (if cholesterol values documented)
- 84165 = Protein, total, serum

SPECIALIZED LAB CODES - MUST NOT MISS:
- 82382 = 24-hour urine collection and analysis (if 24-hour urine ordered or resulted)
  Used for: 24-hour urine metanephrines, 24-hour urine catecholamines, etc.
- 82384 = Plasma free metanephrines or plasma catecholamines (if plasma labs ordered/resulted)
  Used for: Plasma free metanephrines (diagnostic for pheochromocytoma), plasma catecholamines
- 93000 = Electrocardiogram (ECG) - if ECG ordered or performed
- 93010 = Electrocardiogram (ECG) - if ECG with interpretation ordered

CRITICAL FOR PHEOCHROMOCYTOMA: If assessment mentions pheochromocytoma diagnosis:
  Look for ordered/performed: 24-hour urine metanephrines → code 82382
  Look for ordered/performed: plasma metanephrines → code 82384
  Look for ordered/performed: ECG (always ordered for pheo pre-op) → code 93000 or 93010

Example: Plan says "ordered 24-hour urine catecholamines and metanephrines" → code 82382
Example: Plan says "Plasma free metanephrines also elevated" (results back) → code 82384
Example: Plan says "I'm going to order...an ECG" → code 93000

Include if lab values or procedure orders explicitly documented in Objective or Plan
Use confidence 0.90-0.95 if results/orders clearly documented
One code per test type

TYPE 9: CPT PROCEDURE CODES (Non-E/M)
For each procedure/service in Plan section:

CRITICAL: Only code procedures that have been PERFORMED, not planned future procedures.
- If plan says "scheduled for surgery next week" → do NOT code yet
- If procedure results are documented → code it
- If procedure performed during this visit → code it

For each PERFORMED procedure/service in Plan section:
1. Match procedure to standard CPT codes
2. Use modifiers (-LT, -RT) only if laterality explicit
3. Wound repair: SIZE-DEPENDENT (12001=<2.5cm, 12002=2.6-7.5cm, 12004=>7.5cm)
   - If size NOT specified in note, reduce confidence to 0.55-0.60 and flag for review
4. One code per distinct procedure
5. Use confidence 0.85-0.95 for clearly documented procedures

COMMON SURGICAL PROCEDURE CODES (reference, only if performed):
- 60220 = Thyroidectomy
- 60500 = Adrenalectomy (removal of adrenal gland) - laparoscopic or open
- 60522 = Adrenalectomy, laparoscopic (if "laparoscopic adrenalectomy" explicitly performed)
- 12001-12007 = Wound repair by sutures (size dependent)
- 99281-99285 = Emergency department visit codes
Example: Plan says "scheduled for laparoscopic adrenalectomy" → do NOT code yet (not performed)
Example: Objective shows "Post-operative from adrenalectomy" → code 60522

DO NOT confuse:
- Planned future surgery → no CPT code yet
- Chemotherapy session → Z51.11 (different from surgery)
- Pre-operative evaluation → E/M codes (99202-99205), not surgical procedure codes

[CPT CODE SELECTION WHEN MULTIPLE SIMILAR CODES EXIST - APPLIES TO ALL CASES]
This rule applies universally across trauma, imaging, wound repair, and all procedures:

IMAGING PROCEDURES (Chest, extremities, CT, etc.):
- When note specifies view count, use that code exactly
- When note does NOT specify view count:
  * Chest X-ray: Default to 71046 (2 views - standard) not 71045 (single view)
  * Ankle X-ray: Default to 73620 (3 views) not 73610 (single view)
  * Apply same logic to other imaging: Default to standard multi-view unless explicitly documented as "single view only"

CT SCAN CONTRAST SELECTION (CRITICAL FOR ACCURATE CODING):
- Check Plan/Objective for explicit mention of "with contrast" or "without contrast"
- CT ABDOMEN/PELVIS:
  * If note says "with contrast" → 74177 (CT abdomen/pelvis WITH contrast material)
  * If note says "without contrast" → 74176 (CT abdomen/pelvis WITHOUT contrast)
  * If contrast status NOT specified → Default to 74177 (with contrast is standard for most diagnostics)
- CT CHEST:
  * If note says "with contrast" → 71260 (CT thorax WITH contrast)
  * If note says "without contrast" → 71250 (CT thorax WITHOUT contrast)
  * If NOT specified → Default to 71260 (with contrast is standard)
- Apply same logic to other CT scans: Match contrast status to what is documented or default to WITH contrast
- Confidence: 0.90-0.95 for clearly documented procedure AND contrast status

WOUND REPAIR SIZE CODES:
- 12001 (<2.5cm), 12002 (2.6-7.5cm), 12004 (>7.5cm)
- Match to documented size; if size not specified → confidence 0.60, flag for review

E/M CODES (visit complexity):
- Assess MDM from documentation: severity, exam scope, diagnoses count, procedures ordered
- New patient: 99202-99205; Established: 99212-99215
- Match complexity level to documented findings

This approach ensures consistent, evidence-based code selection across ALL medical scenarios.

[SPECIFIC COMMON IMAGING CODES - REQUIRED FOR ACCURACY]
For procedures ordered or mentioned in Plan/Assessment, use EXACT code from list:

COMPUTED TOMOGRAPHY (CT) CODES:
- CT Abdomen/Pelvis:
  * 74150 = CT abdomen/pelvis WITHOUT contrast (if "without contrast" or "non-contrast" stated)
  * 74160 = CT abdomen/pelvis WITH contrast (if "with contrast" stated OR NOT specified - WITH is default standard)
  * 74170 = CT abdomen/pelvis both without AND with contrast (if sequential scans ordered)
- CT Chest/Thorax:
  * 71250 = CT thorax WITHOUT contrast
  * 71260 = CT thorax WITH contrast (if "with contrast" stated OR NOT specified - WITH is default standard)
  * Apply this logic: If contrast status unknown → DEFAULT to WITH contrast code (160, 260, etc.)
  * If explicit "without contrast" documented → use WITHOUT code (150, 250, etc.)

CHEST X-RAYS:
- 71046 = Chest X-ray, 2 views (standard - default if view count not specified)
- 71047 = Chest X-ray, 3 views
- 71048 = Chest X-ray, 4+ views
- If view count not documented → use 71046 (2 views is standard)

ANKLE X-RAYS:
- 73610 = Ankle, single view
- 73620 = Ankle, 3 views (standard - use this as default if not specified)

OTHER IMAGING:
- 99214 = E/M established patient, moderate MDM (NOT imaging - belongs in TYPE 7)

Confidence: 0.90-0.95 for clearly documented imaging procedures with correct code match

[CONFIDENCE SCORING]
- confidence: 0.6-1.0 based on clarity
  * 0.95-1.0: Explicit with full anatomical/lateral details, current injury
  * 0.85-0.94: Clearly documented with details
  * 0.75-0.84: Documented or historical injuries
  * 0.75-0.84: Documented or historical injuries
  * 0.60-0.74: Inferred significantly

- evidence_text: Exact quote from SOAP DIRECTLY supporting THIS code
  * Must match the anatomy mentioned for THIS code
  * Do NOT reuse evidence from other codes

[OUTPUT FORMAT - RETURN ONLY VALID JSON]
{
  "codes": [
    {
      "system": "ICD10",
      "code": "S81.812A",
      "description": "Laceration without foreign body of left lower leg, initial encounter",
      "confidence": 0.95,
      "evidence_text": "Left leg swelling and pain",
      "confidence_reason": "Explicitly documented in assessment"
    },
    {
      "system": "ICD10",
      "code": "S51.811A",
      "description": "Laceration without foreign body of right forearm, initial encounter",
      "confidence": 0.95,
      "evidence_text": "Deep cuts on the right arm",
      "confidence_reason": "Explicitly documented in assessment"
    },
    {
      "system": "ICD10",
      "code": "S43.401A",
      "description": "Unspecified sprain of right shoulder joint, initial encounter",
      "confidence": 0.80,
      "evidence_text": "History of multiple traumatic events including shoulder injury",
      "confidence_reason": "Previous shoulder injury documented"
    },
    {
      "system": "ICD10",
      "code": "V23.4XXA",
      "description": "Motorcycle rider injured in collision with car, initial encounter",
      "confidence": 0.95,
      "evidence_text": "Motorcycle accident on October 5, 2025, car pulled out and hit patient",
      "confidence_reason": "Explicit external cause documented"
    },
    {
      "system": "CPT",
      "code": "12002",
      "description": "Simple wound repair",
      "confidence": 0.85,
      "evidence_text": "Clean and dress arm wounds",
      "confidence_reason": "Procedure documented in plan"
    }
  ]
}

CRITICAL REMINDERS - DO NOT MAKE THESE MISTAKES:

FOR TRAUMA CASES:
1. ✓ code S81.812A (left leg) with "Left leg swelling and pain"
2. ✗ Do NOT code S81.812A (left leg) with "Deep cuts on right arm"
3. ✓ DO include historical injuries if mentioned in assessment
4. ✓ DO include V/W/X/Y codes for trauma
5. ✗ Do NOT copy evidence between codes

FOR CHRONIC DISEASE CASES:
6. ✓ DO include Z-codes for long-term medications (Z79.4 for metformin, Z79.01 for lisinopril)
7. ✓ DO include E/M codes (99214, 99215) for office visits with assessment and plan
8. ✓ DO include lab codes (83036 for HbA1c, 82947 for glucose) if results documented
9. ✓ DO use appropriate E-codes (E11.65 for Type 2 diabetes with hyperglycemia)
10. ✗ Do NOT only generate diagnosis codes; include Z-codes and procedure codes
11. ✗ Do NOT forget CPT E/M codes for office visit encounters

GENERAL:
12. ✓ Evidence text must EXACTLY match documentation for that specific code
13. ✓ High confidence (0.95) requires explicit documentation
14. ✗ Do NOT use high confidence for inferred or implied diagnoses

SOAP Input:
"""


class TwoStagePipeline:
    """
    Two-stage LLM pipeline:
    1. Raw text → Clean SOAP
    2. Clean SOAP → Codes
    """

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
        self.fallback_model = os.getenv("OLLAMA_FALLBACK_MODEL", "qwen2.5:7b-instruct")

    def _call_openrouter(self, prompt: str, system_prompt: str) -> str:
        """Call OpenRouter API."""
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://virtualmedicalcoder.local",
                "X-Title": "Virtual Medical Coder",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
            },
        )

        if response.status_code != 200:
            raise Exception(f"OpenRouter error: {response.text}")

        return response.json()["choices"][0]["message"]["content"]

    def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """Call Ollama fallback."""
        if ollama is None:
            raise Exception("Ollama not installed")

        response = ollama.chat(
            model=self.fallback_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.1},
        )

        if isinstance(response, dict):
            return str(response.get("message", {}).get("content", ""))

        message = getattr(response, "message", None)
        return str(getattr(message, "content", ""))

    def _call_llm(self, prompt: str, system_prompt: str) -> str:
        """Call LLM with fallback."""
        try:
            if self.api_key:
                return self._call_openrouter(prompt, system_prompt)
        except Exception as e:
            print(f"OpenRouter failed: {e}, trying Ollama...")

        try:
            return self._call_ollama(prompt, system_prompt)
        except Exception as e:
            raise Exception(f"Both OpenRouter and Ollama failed: {e}")

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from LLM response."""
        # Try to find JSON block
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Try to parse entire response
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(f"Could not extract JSON from: {text[:200]}")

    def stage_1_normalize_to_soap(self, raw_text: str) -> dict[str, str]:
        """
        Stage 1: Convert messy clinical text to clean SOAP.

        Returns:
            {
                "subjective": "...",
                "objective": "...",
                "assessment": "...",
                "plan": "..."
            }
        """
        print("[Stage 1] Normalizing messy text to clean SOAP...")

        prompt = STAGE_1_NORMALIZE_PROMPT + raw_text

        response = self._call_llm(prompt, "You are a medical documentation specialist.")

        # Extract JSON
        soap_json = self._extract_json(response)

        if not isinstance(soap_json, dict):
            raise ValueError("Stage 1 did not return JSON object")

        # Ensure all SOAP sections exist
        clean_soap = {
            "subjective": str(soap_json.get("subjective", "")).strip(),
            "objective": str(soap_json.get("objective", "")).strip(),
            "assessment": str(soap_json.get("assessment", "")).strip(),
            "plan": str(soap_json.get("plan", "")).strip(),
        }

        # Validate we have data
        if not any(clean_soap.values()):
            raise ValueError("Stage 1 produced empty SOAP note")

        print(f"  ✓ Clean SOAP generated:")
        print(f"    - Subjective: {len(clean_soap['subjective'])} chars")
        print(f"    - Objective: {len(clean_soap['objective'])} chars")
        print(f"    - Assessment: {len(clean_soap['assessment'])} chars")
        print(f"    - Plan: {len(clean_soap['plan'])} chars")

        return clean_soap

    def stage_2_generate_codes(self, clean_soap: dict[str, str]) -> list[dict[str, Any]]:
        """
        Stage 2: Generate codes from clean SOAP.

        Returns:
            [{
                "system": "ICD10",
                "code": "...",
                "description": "...",
                "confidence": 0.9,
                "evidence_text": "...",
                "confidence_reason": "..."
            }, ...]
        """
        print("\n[Stage 2] Generating codes from clean SOAP...")

        soap_text = json.dumps(clean_soap, indent=2)
        prompt = STAGE_2_CODE_GENERATION_PROMPT + soap_text

        response = self._call_llm(prompt, "You are a certified medical coding specialist.")

        # Extract JSON
        codes_json = self._extract_json(response)

        if not isinstance(codes_json, dict):
            raise ValueError("Stage 2 did not return JSON object")

        codes = codes_json.get("codes", [])

        if not isinstance(codes, list):
            raise ValueError("Stage 2 codes is not a list")

        print(f"  ✓ Codes generated:")
        print(f"    - ICD-10: {sum(1 for c in codes if c.get('system') == 'ICD10')}")
        print(f"    - CPT: {sum(1 for c in codes if c.get('system') == 'CPT')}")

        return codes

    def process_complete(self, raw_text: str) -> dict[str, Any]:
        """
        Complete two-stage pipeline:
        Raw text → Clean SOAP → Codes

        Args:
            raw_text: Messy clinical text (any format)

        Returns:
            {
                "clean_soap": {...},
                "codes": [...],
                "stage_1_success": True,
                "stage_2_success": True
            }
        """
        print("="*70)
        print("TWO-STAGE PIPELINE: Raw Text → Clean SOAP → Codes")
        print("="*70)

        # Stage 1
        try:
            clean_soap = self.stage_1_normalize_to_soap(raw_text)
            stage_1_success = True
        except Exception as e:
            print(f"  ✗ Stage 1 failed: {e}")
            stage_1_success = False
            clean_soap = {}

        # Stage 2
        try:
            if stage_1_success:
                codes = self.stage_2_generate_codes(clean_soap)
            else:
                codes = []
            stage_2_success = len(codes) > 0
        except Exception as e:
            print(f"  ✗ Stage 2 failed: {e}")
            stage_2_success = False
            codes = []

        print("\n" + "="*70)
        return {
            "clean_soap": clean_soap,
            "codes": codes,
            "stage_1_success": stage_1_success,
            "stage_2_success": stage_2_success,
        }
