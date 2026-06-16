#!/usr/bin/env python
"""
Final comprehensive test of pheochromocytoma case with ALL fixes applied:
1. Symptom coding decision gate
2. Secondary hypertension rule  
3. Dangerous miscoding prevention
4. Missing lab codes (82382, 82384, 93000)
5. Surgical procedure rules
"""

clinical_text = """Doctor: Come in. So I see you've been referred from Dr. Patel. What's going on?

Patient: Yeah so basically I've been having these really weird episodes. Like I'll be fine and then suddenly everything goes kind of purple-ish and I start shaking — not like a full seizure but more like trembling — and my heart starts racing. It's happened four times in the last six weeks.

Doctor: How long do the episodes last?

Patient: Maybe 5 to 10 minutes and then I feel completely exhausted afterward. I also get these massive headaches — pounding, like my head is going to explode. And I sweat a lot during the episodes even if it's cold.

Doctor: Any history of high blood pressure?

Patient: Yeah they told me I have high blood pressure but it's been really hard to control. I'm on three different medications for it but it still runs high. I'm on amlodipine, metoprolol, and losartan.

Doctor: That combination not working well is actually a very important clue. Any weight changes? Anxiety?

Patient: I've lost about 6 kilos in the last 3 months without trying. And yeah I'm pretty anxious all the time but I thought that was just life you know.

Doctor: Okay, let me check you.
[Examination notes]
BP today: 188/112 mmHg — very elevated. Heart rate 108 bpm irregular. Pallor noted. Mild diaphoresis. Abdomen: no palpable masses.

Doctor: I need to run some tests. I'm going to order 24-hour urine catecholamines and metanephrines, plasma free metanephrines, CT abdomen and pelvis with contrast, and an ECG.

[Three days later — results review]

Doctor: Mr. Hassan, your results are back and I need to talk to you about something serious. Your 24-hour urine metanephrines came back markedly elevated — three times the upper limit of normal. Plasma free metanephrines also elevated. CT abdomen shows a 4.2cm right adrenal mass. Based on all of this, you have a pheochromocytoma — a tumor of the adrenal gland.

Patient: Oh god. Is it cancer?

Doctor: Most are benign — about 90% — but we need to do further workup. I'm referring you to endocrinology and urology. We need to start you on alpha-blocker therapy immediately — phenoxybenzamine 10mg twice daily — before any surgical intervention to control your blood pressure. Do not stop your other blood pressure medications.

Patient: What happens next?

Doctor: Once you're adequately blocked — usually takes 10 to 14 days — we'll schedule laparoscopic adrenalectomy to remove the tumor. You'll need pre-operative clearance including cardiac evaluation first.

Patient: Okay. This is a lot to take in.

Doctor: I understand. We caught this at a good stage. The surgery has excellent outcomes. I'll have my nurse schedule your endocrinology appointment for this week."""

print("=" * 90)
print("FINAL TEST: PHEOCHROMOCYTOMA CASE WITH ALL REGRESSION FIXES")
print("=" * 90)
print("\nTesting 5 critical fixes:")
print("  1. Symptom coding decision gate (no integral symptoms)")
print("  2. Secondary hypertension (I15.2, not I10)")
print("  3. Dangerous miscoding prevention (no R44.3, Z51.11)")
print("  4. Missing lab codes (82382, 82384, 93000)")
print("  5. Surgical procedure rules (no planned surgery codes)")
print("\nAnalyzing clinical text...")
print("-" * 90)

try:
    from nlp_engine.services import MedicalNLPService
    
    service = MedicalNLPService()
    result = service.analyze_raw_text(clinical_text)
    
    print("\n✅ Analysis completed successfully!\n")
    
    # Display codes
    print("=" * 90)
    print(f"GENERATED CODES ({len(result['codes'])} total):")
    print("=" * 90)
    
    icd_codes = [c for c in result['codes'] if c['system'] == 'ICD10']
    cpt_codes = [c for c in result['codes'] if c['system'] == 'CPT']
    
    print(f"\n--- ICD-10 CODES ({len(icd_codes)}) ---")
    for i, code in enumerate(icd_codes, 1):
        code_val = code['code']
        desc = code.get('description', 'N/A')[:70]
        confidence = code.get('confidence', 0)
        flagged = "🚩 FLAGGED" if code.get('needs_review') else "✅"
        print(f"{i}. {code_val:8} | {confidence:.2f} | {flagged} | {desc}")
        if code.get('needs_review'):
            reason = code.get('review_reason', '')[:60]
            print(f"   └─ {reason}")
    
    print(f"\n--- CPT CODES ({len(cpt_codes)}) ---")
    for i, code in enumerate(cpt_codes, 1):
        code_val = code['code']
        desc = code.get('description', 'N/A')[:70]
        confidence = code.get('confidence', 0)
        flagged = "🚩 FLAGGED" if code.get('needs_review') else "✅"
        print(f"{i}. {code_val:8} | {confidence:.2f} | {flagged} | {desc}")
    
    print("\n" + "=" * 90)
    print("VALIDATION RESULTS:")
    print("=" * 90)
    validation = result.get('validation_metadata', {})
    print(f"Total codes generated: {validation.get('total_codes', 0)}")
    print(f"Flagged for review: {validation.get('flagged_count', 0)}")
    print(f"Issues found: {len(validation.get('validation_issues', []))}")
    
    print("\n" + "=" * 90)
    print("EXPECTED RESULTS (All Fixes Applied):")
    print("=" * 90)
    print("""
✅ SHOULD BE PRESENT:
   E27.5  - Pheochromocytoma
   I15.2  - Secondary hypertension (from pheo, NOT I10)
   Z01.810 - Pre-operative cardiovascular evaluation
   99205  - New patient, high complexity E/M
   74160  - CT abdomen/pelvis with contrast
   82382  - 24-hour urine metanephrines
   82384  - Plasma free metanephrines  
   93000  - Electrocardiogram

❌ MUST NOT BE PRESENT (Regression Prevention):
   R00.0  - Tachycardia (integral to pheo)
   R61    - Diaphoresis (integral to pheo)
   R51.9  - Headache (integral to pheo)
   R44.3  - Hallucinations (DANGEROUS - visual disturbance, not hallucination)
   R03.0  - Elevated BP reading (routine for HTN)
   R63.4  - Weight loss (symptom under investigation)
   F41.9  - Anxiety (not physician-confirmed)
   Z51.11 - Chemotherapy (DANGEROUS - surgery ≠ chemotherapy)
   Z79.02 - Antithrombotics (wrong category)
   Z79.899 on phenoxybenzamine (newly prescribed, not long-term)

✅ FIXES VERIFIED IF:
   - No symptom codes coded with decision gate
   - Hypertension is I15.2 (secondary), not I10
   - No R44.3 or Z51.11 present
   - Lab codes 82382, 82384, 93000 present
   - No planned future procedures coded
    """)
    
    print("=" * 90)
    print("TEST COMPLETE - Ready for Claude's audit")
    print("=" * 90)
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
