#!/usr/bin/env powershell
# Test pheochromocytoma case via HTTP API

$clinical_text = @"
Doctor: Come in. So I see you've been referred from Dr. Patel. What's going on?

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

Doctor: I understand. We caught this at a good stage. The surgery has excellent outcomes. I'll have my nurse schedule your endocrinology appointment for this week.
"@

$payload = @{
    file_type = "raw_text"
    raw_text = $clinical_text
} | ConvertTo-Json

Write-Host "=" * 80
Write-Host "TESTING PHEOCHROMOCYTOMA CASE WITH ALL FIXES"
Write-Host "=" * 80
Write-Host "`nSending request to /api/ingestion/process-text/..."
Write-Host "-" * 80

try {
    $response = Invoke-WebRequest `
        -Uri "http://localhost:8000/api/ingestion/process-text/" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json"} `
        -Body $payload `
        -UseBasicParsing `
        -ErrorAction Stop
    
    $result = $response.Content | ConvertFrom-Json
    
    Write-Host "`n✅ Request successful!`n"
    
    # Display codes
    if ($result.icd_codes -or $result.cpt_codes) {
        Write-Host "=" * 80
        Write-Host "GENERATED CODES:"
        Write-Host "=" * 80
        
        $all_codes = @()
        if ($result.icd_codes) {
            $all_codes += $result.icd_codes
        }
        if ($result.cpt_codes) {
            $all_codes += $result.cpt_codes
        }
        
        foreach ($code in $all_codes) {
            $system = $code.system
            $code_val = $code.code
            $desc = $code.description -replace "^(.{50}).*", '$1...'
            $confidence = [math]::Round($code.confidence, 2)
            $flagged = if ($code.needs_review) { "🚩 FLAGGED" } else { "✅ OK" }
            
            Write-Host "`n[$system] $code_val - $flagged"
            Write-Host "  Desc: $desc"
            Write-Host "  Confidence: $confidence"
            if ($code.needs_review) {
                Write-Host "  Reason: $($code.review_reason)"
            }
        }
        
        Write-Host "`n" + "=" * 80
        Write-Host "VALIDATION SUMMARY:"
        Write-Host "=" * 80
        $validation = $result.validation_metadata
        Write-Host "Total codes: $($validation.total_codes)"
        Write-Host "Flagged codes: $($validation.flagged_count)"
        Write-Host "Review status: $($result.review_status)"
    }
    
    Write-Host "`n" + "=" * 80
    Write-Host "TEST COMPLETE"
    Write-Host "=" * 80
    
} catch {
    Write-Host "`n❌ ERROR: $_"
    if ($_.Exception.Response) {
        $errorResponse = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($errorResponse)
        $errorBody = $reader.ReadToEnd()
        Write-Host "Response: $errorBody"
    }
}
