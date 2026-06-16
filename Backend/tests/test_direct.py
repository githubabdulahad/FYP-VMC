from nlp_engine.services import MedicalNLPService

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

print("=" * 80)
print("TESTING PHEOCHROMOCYTOMA CASE WITH ALL FIXES")
print("=" * 80)
print("\nAnalyzing clinical text...")
print("-" * 80)

try:
    service = MedicalNLPService()
    result = service.analyze_raw_text(clinical_text)
    
    print("\n✅ Analysis completed successfully!\n")
    
    # Display codes
    print("=" * 80)
    print(f"GENERATED CODES ({len(result['codes'])} total):")
    print("=" * 80)
    for i, code in enumerate(result['codes'], 1):
        system = code['system']
        code_val = code['code']
        desc = code.get('description', 'N/A')[:60]
        confidence = code.get('confidence', 0)
        flagged = "🚩 FLAGGED" if code.get('needs_review') else "✅ OK"
        print(f"\n{i}. [{system}] {code_val} - {flagged}")
        print(f"   Desc: {desc}")
        print(f"   Confidence: {confidence:.2f}")
        if code.get('needs_review'):
            reason = code.get('review_reason', 'N/A')[:80]
            print(f"   Reason: {reason}")
    
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY:")
    print("=" * 80)
    validation = result.get('validation_metadata', {})
    print(f"Total codes: {validation.get('total_codes', 0)}")
    print(f"Flagged codes: {validation.get('flagged_count', 0)}")
    print(f"Review status: {result.get('review_status', 'N/A')}")
    
    if validation.get('validation_issues'):
        print("\nIssues found:")
        for issue in validation['validation_issues']:
            print(f"  - {issue.get('code')}: {issue.get('issue')}")
    
    print("\n" + "=" * 80)
    print("EXPECTED RESULTS (with fixes):")
    print("=" * 80)
    print("✅ E27.5 (pheochromocytoma)")
    print("✅ I10 (hypertension)")
    print("✅ F41.9 (anxiety)")
    print("✅ 99205 (new patient, high complexity)")
    print("✅ 74160 (CT with contrast) - NOT 74177")
    print("❌ NO Z79.02/Z79.891 (wrong medication codes)")
    print("✅ All codes should have 0 flagged (validated)")
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
