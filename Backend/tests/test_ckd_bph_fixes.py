#!/usr/bin/env python
"""
Test script to validate all CKD/BPH case fixes:
1. Evidence extraction improvements (diagnoses, procedures, symptoms)
2. ICD-10 stage-specific code (N18.31 vs N18.3)
3. Manifestation code detection (N40.1 → R35.0, R35.1)
4. Database description truncation fix
5. Z79.899 restriction for vague references
"""

import json
import sys
import os
import django

sys.path.insert(0, 'D:\\FYP\\Backend\\VirtualMedicalCoder')

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VirtualMedicalCoder.settings')
django.setup()

from nlp_engine.services import analyze_raw_text
from coding.evidence_extractor import EvidenceExtractor

# Test case: CKD stage 3a + BPH with LUTS
test_raw_text = """Patient: Robert Chen, 58-year-old male
Date of Visit: May 28, 2026
Visit Type: Established patient follow-up

Chief Complaint: Follow-up for chronic kidney disease (CKD) and benign prostatic hyperplasia (BPH).

History of Present Illness:
Patient presents for routine monitoring of stage 3 CKD and BPH. He notes consistent compliance with his current medications. Reports moderate urinary frequency and nocturia (awakening 3 times per night), which has mildly worsened over the last month. Denies dysuria, hematuria, flank pain, or peripheral edema. Energy levels are baseline.

Vital Signs:
Blood Pressure: 126/74 mmHg
Pulse: 72 bpm
Temperature: 98.2°F
Weight: 195 lbs
eGFR: 44 mL/min/1.73m²
Serum Creatinine: 1.6 mg/dL

Physical Examination:
General: Well-developed, well-nourished, in no acute distress
Abdomen: Soft, non-tender, no organomegaly or palpable bladder
Extremities: Trace ankle edema bilaterally, symmetric; peripheral pulses 2+ 
Genitourinary: Digital rectal exam (DRE) reveals an enlarged, smooth, non-tender prostate without discrete nodules.

Assessment:
1. Chronic kidney disease, stage 3a — stable, monitoring renal function
2. Benign prostatic hyperplasia with lower urinary tract symptoms (LUTS) — mildly progressed

Plan:
Continue current renal protection strategies; avoid NSAIDs.
Initiate tamsulosin 0.4mg daily at bedtime for worsening urinary symptoms.
Order basic metabolic panel (BMP) to recheck creatinine and eGFR in 3 months.
Counseled on fluid restriction prior to bedtime.
Follow-up in 3 months."""

print("=" * 80)
print("TEST: CKD/BPH Case with All Fixes")
print("=" * 80)

# Test 1: Run full pipeline
print("\n[TEST 1] Full Pipeline Execution")
print("-" * 80)
try:
    result = analyze_raw_text(test_raw_text)
    print("✓ Pipeline executed successfully")
    
    # Save output for inspection
    with open('test_ckd_bph_output.json', 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print("✓ Output saved to test_ckd_bph_output.json")
except Exception as e:
    print(f"✗ Pipeline failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Validate SOAP extraction
print("\n[TEST 2] SOAP Note Extraction")
print("-" * 80)
soap = result.get('soap_note', {})
print(f"Subjective: {soap.get('subjective')[:80]}...")
print(f"Objective: {soap.get('objective')[:80]}...")
print(f"Assessment: {soap.get('assessment')[:80]}...")
print(f"Plan: {soap.get('plan')[:80]}...")

# Test 3: Check extracted evidence
print("\n[TEST 3] Extracted Evidence Quality")
print("-" * 80)
evidence = result.get('extracted_evidence', {})

print("\n  Diagnoses extracted:")
diagnoses = evidence.get('diagnoses', [])
for diag in diagnoses:
    print(f"    - {diag.get('condition')} (stage: {diag.get('stage')}, severity: {diag.get('severity')})")

# Validate CKD stage extraction
ckd_found = False
for diag in diagnoses:
    if 'chronic kidney disease' in diag.get('condition', '').lower():
        ckd_found = True
        if diag.get('stage') == '3a':
            print("    ✓ CKD Stage 3a correctly extracted")
        else:
            print(f"    ✗ CKD Stage NOT correctly extracted (got: {diag.get('stage')})")

print("\n  Procedures extracted:")
procedures = evidence.get('procedures', [])
for proc in procedures:
    print(f"    - {proc.get('name')[:60]}... (approach: {proc.get('approach')})")

print("\n  Symptoms extracted:")
symptoms = evidence.get('symptoms', [])
for symptom in symptoms:
    print(f"    - {symptom}")

# Check symptom extraction
expected_symptoms = ['urinary frequency', 'nocturia', 'ankle edema']
found_symptoms = [s for s in symptoms if any(exp in s.lower() for exp in expected_symptoms)]
if len(found_symptoms) >= 2:
    print(f"  ✓ Critical symptoms detected: {len(found_symptoms)}/{len(expected_symptoms)}")
else:
    print(f"  ⚠ Missing symptoms: expected {expected_symptoms}, found {found_symptoms}")

print("\n  Vital findings extracted:")
findings = evidence.get('findings', [])
for finding in findings:
    print(f"    - {finding.get('name')}: {finding.get('value')} ({finding.get('type')})")

# Test 4: Check ICD-10 codes
print("\n[TEST 4] ICD-10 Code Generation & Database Descriptions")
print("-" * 80)
icd_codes = result.get('icd_codes', [])
print(f"Total ICD-10 codes: {len(icd_codes)}\n")

critical_codes = {
    'N18.31': 'CKD stage 3a (with correct 5th char)',
    'N40.1': 'BPH with LUTS',
    'R35.0': 'Urinary frequency (manifestation)',
    'R35.1': 'Nocturia (manifestation)',
}

for code_check, description in critical_codes.items():
    found = False
    for code in icd_codes:
        if code.get('code') == code_check:
            found = True
            db_desc = code.get('db_description', '')
            # Check for truncation (should be full description, not cut off at 58 chars)
            if len(db_desc) < 50 and 'symp' in db_desc:  # Old truncated version has "symp"
                print(f"  ✗ {code_check}: TRUNCATED db_description: '{db_desc}'")
            else:
                print(f"  ✓ {code_check}: {description}")
                print(f"     db_description: '{db_desc[:70]}'")
            break
    if not found:
        print(f"  ✗ MISSING: {code_check}")

# Test 5: Check Z-codes
print("\n[TEST 5] Z-Code Generation (Z79.899 restriction)")
print("-" * 80)

# Should NOT have Z79.899 for "renal protection strategies" (vague reference)
z_codes = result.get('icd_codes', []) + result.get('cpt_codes', [])
z79_codes = [c for c in icd_codes if c.get('code', '').startswith('Z79')]
print(f"Z79 codes found: {len(z79_codes)}")

z79_899_found = any(c.get('code') == 'Z79.899' for c in icd_codes)
if z79_899_found:
    z79_evidence = [c.get('evidence_text', '')[:50] for c in icd_codes if c.get('code') == 'Z79.899']
    print(f"  ⚠ Z79.899 found (check if justified)")
    print(f"     Evidence: {z79_evidence}")
else:
    print(f"  ✓ Z79.899 NOT generated (correct - vague reference to 'renal protection strategies')")

for code in z79_codes:
    print(f"    - {code.get('code')}: {code.get('description')}")

# Test 6: Check CPT codes
print("\n[TEST 6] CPT Code Generation")
print("-" * 80)
cpt_codes = result.get('cpt_codes', [])
print(f"Total CPT codes: {len(cpt_codes)}\n")

expected_cpt = {
    '99214': 'Established patient E/M (moderate complexity)',
    '80048': 'Basic metabolic panel (BMP)',
}

for code_check, description in expected_cpt.items():
    found = any(c.get('code') == code_check for c in cpt_codes)
    if found:
        print(f"  ✓ {code_check}: {description}")
    else:
        print(f"  ✗ MISSING: {code_check}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

# Calculate score
score = 0
max_score = 10

# Check 1: CKD stage 3a
if any(c.get('code') == 'N18.31' for c in icd_codes):
    score += 1
    print("✓ CKD stage 3a correctly coded as N18.31 (not N18.3)")
else:
    print("✗ CKD stage 3a NOT correctly coded")

# Check 2: N40.1 present
if any(c.get('code') == 'N40.1' for c in icd_codes):
    score += 1
    print("✓ N40.1 (BPH with LUTS) coded")
else:
    print("✗ N40.1 NOT coded")

# Check 3: R35.0 present (urinary frequency)
if any(c.get('code') == 'R35.0' for c in icd_codes):
    score += 1
    print("✓ R35.0 (Urinary frequency) manifestation code present")
else:
    print("✗ R35.0 manifestation code MISSING")

# Check 4: R35.1 present (nocturia)
if any(c.get('code') == 'R35.1' for c in icd_codes):
    score += 1
    print("✓ R35.1 (Nocturia) manifestation code present")
else:
    print("✗ R35.1 manifestation code MISSING")

# Check 5: No truncated description
truncated_found = any(
    c.get('db_description', '').endswith('symp') 
    for c in icd_codes + cpt_codes
)
if not truncated_found:
    score += 1
    print("✓ No truncated db_descriptions (database fix applied)")
else:
    print("✗ Truncated descriptions found (database fix NOT applied)")

# Check 6: Z79.899 not present (vague reference)
if not z79_899_found:
    score += 1
    print("✓ Z79.899 correctly NOT coded (vague 'renal protection strategies')")
else:
    print("✗ Z79.899 incorrectly coded for vague reference")

# Check 7: Symptoms extracted correctly
if 'urinary frequency' in symptoms or 'frequency' in ' '.join(symptoms):
    score += 1
    print("✓ Urinary frequency symptom extracted")
else:
    print("✗ Urinary frequency symptom NOT extracted")

# Check 8: Nocturia extracted
if 'nocturia' in symptoms or 'nocturia' in ' '.join(symptoms):
    score += 1
    print("✓ Nocturia symptom extracted")
else:
    print("✗ Nocturia symptom NOT extracted")

# Check 9: Ankle edema extracted
if 'ankle edema' in ' '.join(symptoms):
    score += 1
    print("✓ Ankle edema symptom extracted")
else:
    print("✗ Ankle edema symptom NOT extracted")

# Check 10: E/M code present
if any(c.get('code') == '99214' for c in cpt_codes):
    score += 1
    print("✓ Established patient E/M code (99214) present")
else:
    print("✗ E/M code NOT present")

print(f"\nFinal Score: {score}/{max_score}")
if score >= 8:
    print("✓ TEST PASSED - All major fixes applied successfully!")
elif score >= 6:
    print("⚠ PARTIAL PASS - Some issues remain")
else:
    print("✗ TEST FAILED - Major fixes not working")

print("\nFor detailed analysis, check test_ckd_bph_output.json")
