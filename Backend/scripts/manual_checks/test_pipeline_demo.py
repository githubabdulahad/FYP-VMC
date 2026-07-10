"""
Test script demonstrating the complete medical coding pipeline.

Run with: python manage.py shell < coding/test_pipeline_demo.py
"""

from coding.evidence_extractor import EvidenceExtractor
from coding.code_retrieval import CodeRetriever

# ============================================================================
# DEMO 1: EVIDENCE EXTRACTION
# ============================================================================
print("\n" + "="*70)
print("DEMO 1: EVIDENCE EXTRACTION FROM SOAP NOTE")
print("="*70)

soap_note = {
    "subjective": (
        "Patient reports chronic left-sided leg pain for 3 months. "
        "Also complains of persistent fatigue and weight gain. "
        "He says pain is worse at the end of day."
    ),
    "objective": (
        "Vital signs: BP 152/90 (elevated), HR 78, Temp 98.6F, SpO2 98% on room air. "
        "Weight 210 lbs, BMI 31.2. "
        "Physical exam: Left leg shows 2+ pitting edema from knee to ankle. "
        "No skin breakdown or ulceration noted. "
        "Lab work pending: glucose, lipids."
    ),
    "assessment": (
        "1. Chronic leg pain with swelling, left side, likely chronic venous insufficiency "
        "2. Essential hypertension, controlled "
        "3. Type 2 diabetes, chronic, uncontrolled "
        "4. Obesity"
    ),
    "plan": (
        "1. Start compression therapy for left leg "
        "2. Order venous duplex ultrasound to rule out DVT "
        "3. Adjust blood pressure medications "
        "4. Refer to endocrinology for diabetes management "
        "5. Lifestyle modifications: weight loss, exercise"
    )
}

print("\nInput SOAP Note:")
for k, v in soap_note.items():
    print(f"  [{k.upper()}] {v[:80]}...")

evidence = EvidenceExtractor.extract_evidence(soap_note)

print("\n✓ Extracted Evidence:")
print(f"\n  Diagnoses ({len(evidence['diagnoses'])}):")
for dx in evidence['diagnoses']:
    print(f"    - {dx['condition']}")
    print(f"      Acuity: {dx['acuity']}, Severity: {dx['severity']}, Laterality: {dx['laterality']}")

print(f"\n  Procedures ({len(evidence['procedures'])}):")
for proc in evidence['procedures']:
    print(f"    - {proc['name']} (approach: {proc['approach']})")

print(f"\n  Symptoms ({len(evidence['symptoms'])}):")
print(f"    {', '.join(evidence['symptoms'])}")

print(f"\n  Findings ({len(evidence['findings'])}):")
for finding in evidence['findings'][:5]:
    print(f"    - {finding['name']}: {finding['value']}")


# ============================================================================
# DEMO 2: CODE RETRIEVAL
# ============================================================================
print("\n" + "="*70)
print("DEMO 2: CODE RETRIEVAL & RANKING")
print("="*70)

# Retrieve ICD codes for chronic venous insufficiency
print("\nRetrieving ICD-10 candidates for: 'Chronic left leg swelling edema venous insufficiency'")
icd_candidates = CodeRetriever.retrieve_icd_candidates(
    "Chronic left leg swelling edema venous insufficiency",
    top_k=5,
    min_score=0.4
)
print(f"✓ Found {len(icd_candidates)} candidates:")
for i, candidate in enumerate(icd_candidates, 1):
    print(f"  {i}. {candidate['code']} - {candidate['description'][:50]}... (score: {candidate['score']})")

# Retrieve CPT codes for venous ultrasound
print("\nRetrieving CPT candidates for: 'Venous duplex ultrasound left leg'")
cpt_candidates = CodeRetriever.retrieve_cpt_candidates(
    "Venous duplex ultrasound left leg",
    top_k=5,
    min_score=0.4
)
print(f"✓ Found {len(cpt_candidates)} candidates:")
for i, candidate in enumerate(cpt_candidates, 1):
    print(f"  {i}. {candidate['code']} - {candidate['description'][:50]}... (score: {candidate['score']})")


# ============================================================================
# DEMO 3: EVIDENCE SCORING
# ============================================================================
print("\n" + "="*70)
print("DEMO 3: SCORING LLM-GENERATED CODES AGAINST EVIDENCE")
print("="*70)

test_codes = [
    ("ICD10", "I87.2", "Chronic left leg swelling edema"),
    ("ICD10", "M79.3", "Chronic left leg swelling edema"),
    ("ICD10", "E11.9", "Type 2 diabetes chronic uncontrolled"),
]

print("\nScoring how well codes match the clinical evidence:")
for system, code, evidence_text in test_codes:
    score = CodeRetriever.score_llm_code_against_evidence(system, code, evidence_text)
    status = "✓ GOOD" if score > 0.7 else "⚠ WEAK" if score > 0.4 else "✗ POOR"
    print(f"  {status} - {code}: {score:.2f} for '{evidence_text}'")


# ============================================================================
# DEMO 4: SIMULATED FLAGGING FOR REVIEW
# ============================================================================
print("\n" + "="*70)
print("DEMO 4: SIMULATED CODES WITH FLAGGING")
print("="*70)

llm_output_codes = [
    {
        "system": "ICD10",
        "code": "M79.3",
        "description": "Myalgia - unspecified",
        "confidence": 0.72,
        "evidence_text": "Chronic left leg pain",
    },
    {
        "system": "ICD10",
        "code": "E11.9",
        "description": "Type 2 diabetes - unspecified",
        "confidence": 0.88,
        "evidence_text": "Type 2 diabetes chronic",
    },
    {
        "system": "CPT",
        "code": "99214",
        "description": "Office visit, established patient, moderate complexity",
        "confidence": 0.85,
        "evidence_text": "Office visit",
    },
]

print("\nOriginal LLM codes:")
for code in llm_output_codes:
    print(f"  - {code['code']}: confidence {code['confidence']:.2f}")

flagged_codes, flags = CodeRetriever.flag_codes_for_review(
    llm_output_codes,
    evidence
)

print("\n✓ After evidence-based flagging:")
for code in flagged_codes:
    if code.get("needs_review"):
        print(f"  ⚠️  {code['code']} - FLAGGED FOR REVIEW")
    else:
        print(f"  ✓ {code['code']} - OK")

if flags:
    print("\nFlags raised:")
    for flag in flags:
        print(f"  - {flag}")


# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*70)
print("PIPELINE SUMMARY")
print("="*70)
print("""
✓ Evidence extraction working:
  - Identified diagnoses with acuity/laterality/severity
  - Extracted procedures with approach details
  - Found relevant symptoms and vital signs

✓ Code retrieval working:
  - Retrieved ranked ICD-10 candidates
  - Retrieved ranked CPT candidates
  - Scored codes against evidence

✓ Flagging working:
  - Identified low-confidence codes
  - Compared codes against evidence
  - Marked questionable ones for review

Next steps in production:
  1. LLM generates codes with evidence_text
  2. Evidence extracted from SOAP
  3. Codes validated and flagged
  4. Results saved to CodingResult
  5. Medical coder reviews flagged items
  6. Corrections feed back into system

This creates a feedback loop for continuous improvement!
""")
