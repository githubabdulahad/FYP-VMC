import json
import os
import re
from typing import Any

import requests
from coding.validation import validator
from coding.evidence_extractor import EvidenceExtractor
from coding.code_retrieval import CodeRetriever
from coding.diagnosis_parser import ClinicalNarrativeParser
from coding.diagnosis_mapper import DiagnosisToCodeMapper

try:
  import ollama
except ImportError:  # pragma: no cover - optional dependency for fallback runtime only
  ollama = None

SYSTEM_PROMPT = """You are a certified medical coding and clinical documentation specialist with expertise across all medical specialties including but not limited to cardiology, oncology, orthopedics, neurology, psychiatry, pediatrics, obstetrics, pulmonology, gastroenterology, nephrology, and general surgery.

You will receive RAW clinical text from any medical context. Your job is to produce two outputs:
1. A structured SOAP note
2. Accurate medical codes (ICD-10, CPT)

Follow every step in order. Do not skip any step.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — EXTRACT CLINICAL FACTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read the entire input. Extract only clinically relevant information under these categories:

  [SYMPTOMS]     What the patient reports (pain, fatigue, nausea, etc.)
  [DURATION]     How long symptoms have been present
  [VITALS]       Blood pressure, pulse, temperature, SpO2, weight, BMI, etc.
  [EXAM]         Clinician observations on physical examination
  [LABS]         Lab values, imaging results, pathology, ECG, cultures, biopsies
  [DIAGNOSES]    Conditions explicitly stated as confirmed
  [PROCEDURES]   Interventions performed or planned (any specialty)
  [MEDICATIONS]  Drugs prescribed or documented as ongoing
  [HISTORY]      Relevant past medical, surgical, or family history
  [PLAN]         Follow-up, referrals, discharge instructions, tests ordered

Ignore greetings, administrative text, and non-clinical conversation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — APPLY NEGATION AND UNCERTAINTY FILTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before assigning any code, check every diagnosis and finding against this filter.

DO NOT CODE conditions accompanied by:
  Negation    → "no", "denies", "without", "absent", "negative for", "ruled out"
  Uncertainty → "possible", "probable", "suspected", "rule out", "may be",
                "cannot exclude", "differential includes", "query", "versus"

ONLY CODE conditions confirmed by language such as:
  "diagnosis:", "confirmed", "impression:", "consistent with", "known case of",
  "acute", "chronic", "established", "positive for", "presents with"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — BUILD THE SOAP NOTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Using only facts extracted in Step 1, populate each SOAP section:

  Subjective  → Patient-reported symptoms, complaints, history, and duration
  Objective   → Vitals, physical exam findings, lab/imaging/test results
                IMPORTANT: Scan the ENTIRE input — objective data may appear
                anywhere in the note, not only in a dedicated exam section
  Assessment  → Confirmed diagnoses only (never uncertain or negated conditions)
  Plan        → Treatments, medications prescribed, procedures ordered, follow-up

RULE: No section may be left blank or empty.
      If a section has no data in the input, write exactly:
      "Not documented in provided note"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — ASSIGN ICD-10 CODES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Assign one ICD-10 code per confirmed diagnosis from Step 2.

HOW TO SELECT THE CORRECT ICD-10 CODE:

  A. Identify the confirmed diagnosis name exactly as stated in the note.

  B. Apply maximum specificity — always choose the most detailed code available:
     • Include the type/subtype if documented (e.g., Type 1 vs Type 2 diabetes)
     • Include laterality if documented (right vs left)
     • Include acuity if documented (acute vs chronic vs acute-on-chronic)
     • Include anatomical site if documented (inferior wall, anterior wall, etc.)
     • Include stage or severity if documented (Stage III, mild, severe)

  C. ICD-10-CM SELECTION LOGIC — use this elimination process:

     For every diagnosis, ask these questions IN ORDER before selecting a code:

     Q1: Is there a complication documented?
         (abscess, perforation, peritonitis, gangrene, hemorrhage, etc.)
         → YES: use the complication-specific subcode
         → NO:  eliminate all complication subcodes from consideration

     Q2: Is a specific anatomical site, laterality, or type documented?
         → YES: use the site/type-specific subcode
         → NO:  move to the next level of specificity

     Q3: Is acuity documented? (acute vs chronic vs acute-on-chronic)
         → YES: use the acuity-specific subcode
         → NO:  use the unspecified acuity code

     Q4: After applying Q1-Q3, if still uncertain between two codes:
         → Choose the LESS severe / LESS specific code
         → Set confidence to 0.75 or below
         → Explain in confidence_reason

     APPENDICITIS EXAMPLE (apply this logic universally):
       Note says "acute appendicitis, no abscess, no perforation"
       Q1 → No complication documented → eliminate K35.0, K35.2, K35.3
       Q2 → No specific type → move on
       Q3 → Acute documented → confirmed acute
       Result → K35.89 (acute appendicitis without abscess or perforation)

  D. Apply these universal ICD-10 logic rules:
     • A code for an "initial encounter" applies to the first time a condition
       is being treated — use 7th character "A" where applicable
     • A code for a "subsequent encounter" applies to follow-up care
     • "Unspecified" codes (ending in .9 or similar) are last resort only —
       use them only when no further detail is available in the note
     • When a patient is on long-term medications, add the appropriate
       Z79.x code (e.g., Z79.4 for long-term insulin use)
     • Signs and symptoms are coded only when no confirmed diagnosis exists
       that explains them

  E. Do NOT code:
     • Conditions that are historical and not active this encounter
       (unless they affect current management)
     • Conditions ruled out or uncertain (already filtered in Step 2)
     • Normal findings or negative results

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — ASSIGN CPT CODES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Assign one CPT code per procedure or service documented in the note.

HOW TO SELECT THE CORRECT CPT CODE:

  A. EXTRACT FIRST — identify the exact procedure or service name as written
     in the note. Do not infer procedures that are not explicitly documented.

  B. MATCH SPECIFICALLY — select the CPT code that matches the procedure
     description as precisely as possible:
     • Approach matters: open vs laparoscopic vs endoscopic vs percutaneous
     • Complexity matters: simple vs complicated vs with complications
     • Site matters: which organ, which region, which side
     • Emergency vs elective matters for some procedures

  C. CPT SELECTION ANTI-HALLUCINATION RULE:
     Before writing any CPT code number, state the procedure name
     and its approach (open/laparoscopic/endoscopic) out loud in
     your reasoning. Then match ONLY to that specific approach.

     Common procedure approach mappings (apply this universally):
       "laparoscopic appendectomy"    → 44970 ONLY
       "open appendectomy"             → 44950 or 44960 (if complicated)
       "laparoscopic cholecystectomy"  → 47562-47564 (by complexity)
       "open cholecystectomy"          → 47600-47620 (by complexity)

     If you cannot find the procedure in your knowledge with high
     confidence, set confidence to 0.60 and flag it:
       "confidence_reason": "CPT code uncertain — manual verification recommended"

     NEVER assign a CPT code that does not match the documented approach
     and procedure name.

  D. FOR EVALUATION & MANAGEMENT (E/M) CODES — use exactly ONE per encounter:
     New patient visits      → 99202 to 99205 (low to high complexity)
     Established patient     → 99212 to 99215 (low to high complexity)

     To determine E/M level, assess Medical Decision Making (MDM):
       Low complexity (99212-99213):
         → 1 self-limited or minor problem
         → 1 stable chronic condition
         → Simple data review, no additional workup needed

       Moderate complexity (99214):
         → 2 or more chronic conditions addressed this visit
         → 1 new problem requiring additional workup or referral
         → Review of external records or independent test interpretation

       High complexity (99215):
         → Severe exacerbation of chronic illness
         → New problem threatening life or bodily function
         → Extensive data review and high-risk management decisions

     TIEBREAKER: If MDM level cannot be determined from documentation alone,
     always select the LOWER complexity code and note:
       "downgrade_reason": "MDM level ambiguous — downgraded per documentation guidelines"

  E. NEVER:
     • Assign a general or exploratory procedure code when the note names a
       specific definitive procedure
     • Assign two E/M codes for the same encounter
     • Invent a procedure not explicitly documented in the note
     • Use a code from memory without matching it to the documented procedure name
     • Use a CPT code that does not match the documented surgical approach

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — OMIT SNOMED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SNOMED is not required in this system. Do not output SNOMED codes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 7 — CONFIDENCE SCORING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every code must receive a confidence score. The score must be derived from
the evidence in the note — never assumed or defaulted.

BASE SCORE — start here:
  1.00 → Exact diagnosis or procedure name is present verbatim in the note
  0.85 → Strong clinical indicators present; diagnosis clearly implied
  0.70 → Diagnosis or procedure inferred from contextual clues only

MANDATORY CEILINGS — apply these on top of the base score:
  Procedure not named explicitly (inferred from context)     → cap at 0.80
  Two or more codes are equally plausible                    → cap at 0.75
  Condition documented in history, not active this visit     → cap at 0.70
  Condition confirmed but with minimal supporting detail     → cap at 0.65

You MUST provide a "confidence_reason" field for every code explaining in
one sentence why that specific score was assigned.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 8 — OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY valid JSON. No markdown, no explanations, no text before or after.

{
  "soap": {
    "subjective": "...",
    "objective": "...",
    "assessment": "...",
    "plan": "..."
  },
  "codes": [
    {
      "system": "ICD10",
      "code": "...",
      "description": "...",
      "confidence": 0.00,
      "confidence_reason": "One sentence explaining this score",
      "evidence_text": "Exact phrase copied from the input note"
    },
    {
      "system": "CPT",
      "code": "...",
      "description": "...",
      "confidence": 0.00,
      "confidence_reason": "One sentence explaining this score",
      "evidence_text": "Exact phrase copied from the input note"
    },
    
  ]
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL SELF-CHECK — verify all before outputting
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ☑ All four SOAP sections are filled — none are empty strings
  ☑ No codes assigned for negated or uncertain conditions
  ☑ Each ICD-10 code uses maximum available specificity
  ☑ Each CPT code matches an explicitly named procedure or service
  ☑ Exactly one E/M code per encounter (if applicable)
  ☑ Every code includes confidence_reason and evidence_text
  ☑ Output is valid JSON only — no text before or after the braces
"""


CONVERSATION_NORMALIZER_PROMPT = """You are a clinical transcription specialist.
You will receive a raw doctor-patient conversation or messy clinical text.
Your job is to convert it into a structured clinical note that a medical coder can process.

RULES:
1. Extract only medically relevant information — ignore greetings,
   small talk, and location/social details unless clinically relevant
2. Separate CURRENT visit findings from HISTORICAL incidents
3. Never diagnose — only document what is stated or clearly implied
4. Write in third-person clinical language
5. Be concise — remove conversational filler

OUTPUT FORMAT — return plain text in this structure:

CURRENT VISIT
  Date of Visit: [date if mentioned, else "Not documented"]
  Chief Complaint: [primary reason for today's visit]
  Symptoms: [symptoms reported for current visit only]
  Mechanism of Injury: [how current injury occurred, if applicable]
  Examination Findings: [any physical findings mentioned]
  Investigations Ordered: [tests ordered this visit]
  Plan: [treatment plan, medications, follow-up]
  Confirmed Diagnoses: [only if doctor explicitly states a diagnosis]

HISTORY OF PRESENT ILLNESS
  [List each prior incident chronologically with date, mechanism,
   and injuries — clearly labeled as historical]

Return ONLY the structured note. No explanations.
"""

class NLPProcessingError(Exception):
    pass


def _extract_json_block(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or start >= end:
            raise NLPProcessingError("Model response did not contain valid JSON.")
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise NLPProcessingError("Failed to parse model JSON response.") from exc


def _extract_response_content(response: dict) -> str:
    """Extract content from OpenRouter API response."""
    try:
        # OpenRouter returns: {"choices": [{"message": {"content": "..."}}]}
        return response.get("choices", [{}])[0].get("message", {}).get("content", "")
    except (IndexError, KeyError, TypeError):
        return ""


def _call_openrouter_with_system(system_prompt: str, user_text: str, selected_model: str, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/yourusername/VirtualMedicalCoder",
        "X-Title": "Virtual Medical Coder",
    }

    payload = {
        "model": selected_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.1,
    }

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    response_json = response.json()

    if "error" in response_json:
        error_msg = response_json.get("error", {}).get("message", "Unknown error")
        raise NLPProcessingError(f"OpenRouter API error: {error_msg}")

    return _extract_response_content(response_json)


def _call_ollama_with_system(system_prompt: str, user_text: str, fallback_model: str) -> str:
    if ollama is None:
        raise NLPProcessingError(
            "Ollama fallback is unavailable because 'ollama' is not installed."
        )

    response = ollama.chat(
        model=fallback_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        options={"temperature": 0.1},
    )

    if isinstance(response, dict):
        return str(response.get("message", {}).get("content", ""))
    message = getattr(response, "message", None)
    return str(getattr(message, "content", ""))


def detect_conversation(text: str) -> bool:
    """Heuristic detection for dialogue-heavy or messy clinical text."""
    if not text or not isinstance(text, str):
        return False

    indicators = [
        "Doctor:",
        "Patient:",
        "Dr.",
        "patient said",
        "asked the patient",
        "patient reports that",
        "she said",
        "he said",
        "they said",
    ]
    lowered = text.lower()
    matches = sum(1 for item in indicators if item.lower() in lowered)
    return matches >= 2


def _normalize_clinical_text(raw_text: str) -> str:
    """Normalize dialogue-heavy input into a cleaner note for the coding model."""
    text = (raw_text or "").strip()
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned_lines = []
    for line in text.split("\n"):
        normalized_line = re.sub(r"\s+", " ", line).strip()
        if normalized_line:
            cleaned_lines.append(normalized_line)

    text = "\n".join(cleaned_lines)

    if detect_conversation(text):
        text = re.sub(
            r"\s+(?=(?:Doctor|Patient|Clinician|Nurse|Provider)\s*:)",
            "\n",
            text,
            flags=re.IGNORECASE,
        )

    return re.sub(r"\n{3,}", "\n\n", text)


def _normalize_system(raw_system: Any) -> str | None:
    if raw_system is None:
        return None
    value = str(raw_system).strip().upper().replace("-", "").replace(" ", "")
    mapping = {
        "ICD10": "ICD10",
        "ICD": "ICD10",
        "CPT": "CPT",
    }
    return mapping.get(value)


def _filter_coding_results(codes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = []
    for item in codes:
        if not isinstance(item, dict):
            continue
        system = _normalize_system(item.get("system"))
        code = str(item.get("code", "")).strip()
        if system not in {"ICD10", "CPT"} or not code:
            continue
        filtered.append(
            {
                "system": system,
                "code": code,
                "description": str(item.get("description", "")).strip() or "LLM suggested code",
                "confidence": _normalize_confidence(item.get("confidence", 0.5)),
                "confidence_reason": str(item.get("confidence_reason", "")).strip(),
                "evidence_text": str(item.get("evidence_text", "")).strip(),
            }
        )
    return filtered


def _call_openrouter(raw_text: str, selected_model: str, api_key: str) -> str:
    headers = {
      "Authorization": f"Bearer {api_key}",
      "Content-Type": "application/json",
      "HTTP-Referer": "https://github.com/yourusername/VirtualMedicalCoder",
      "X-Title": "Virtual Medical Coder",
    }

    payload = {
      "model": selected_model,
      "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Clinical note:\n{raw_text}"},
      ],
      "temperature": 0.1,
    }

    response = requests.post(
      "https://openrouter.ai/api/v1/chat/completions",
      headers=headers,
      json=payload,
      timeout=60,
    )
    response.raise_for_status()
    response_json = response.json()

    if "error" in response_json:
      error_msg = response_json.get("error", {}).get("message", "Unknown error")
      raise NLPProcessingError(f"OpenRouter API error: {error_msg}")

    return _extract_response_content(response_json)


def _call_ollama_fallback(raw_text: str, fallback_model: str) -> str:
    if ollama is None:
      raise NLPProcessingError(
        "Ollama fallback is unavailable because 'ollama' is not installed."
      )

    response = ollama.chat(
      model=fallback_model,
      messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Clinical note:\n{raw_text}"},
      ],
      options={"temperature": 0.1},
    )

    if isinstance(response, dict):
      return str(response.get("message", {}).get("content", ""))
    message = getattr(response, "message", None)
    return str(getattr(message, "content", ""))


def _normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5

    if confidence < 0:
        return 0.0
    if confidence > 1:
        return 1.0
    return confidence


def analyze_raw_text(raw_text: str, model: str | None = None) -> dict[str, Any]:
    """
    Two-stage analysis pipeline:
    Stage 1: Convert messy text → Clean SOAP
    Stage 2: Generate codes from clean SOAP
    
    This is more reliable than trying to extract both SOAP and codes in one LLM call,
    because each stage is focused on a single task.
    
    Environment variables:
    - OPENROUTER_API_KEY: Optional for primary call; if missing, uses Ollama fallback.
    - OPENROUTER_MODEL: Optional. Model to use (default: deepseek/deepseek-chat)
    - OLLAMA_FALLBACK_MODEL: Optional. Local fallback model
      (default: qwen2.5:7b-instruct)
    """
    from nlp_engine.two_stage_pipeline import TwoStagePipeline
    
    # Run two-stage pipeline
    pipeline = TwoStagePipeline()
    result = pipeline.process_complete(raw_text)
    
    if not result["stage_1_success"] or not result["stage_2_success"]:
        raise NLPProcessingError(
            f"Pipeline failed - Stage 1: {result['stage_1_success']}, Stage 2: {result['stage_2_success']}"
        )
    
    clean_soap = result["clean_soap"]
    raw_codes = result["codes"]
    
    # Extract structured evidence from the clean SOAP
    extracted_evidence = EvidenceExtractor.extract_evidence(clean_soap)
    
    # Validate and correct codes
    corrected_codes: list[dict[str, Any]] = []
    validation_issues = []
    flagged_count = 0
    
    for item in raw_codes:
        system = _normalize_system(item.get("system"))
        code = str(item.get("code", "")).strip()
        evidence = item.get("evidence_text") or raw_text
        confidence = float(item.get("confidence", 0.6))
        
        # Validate code against database
        is_valid, reason, db_desc = validator.validate_code(system, code)
        
        if is_valid:
            # Code is valid, attach canonical description
            if db_desc:
                item["db_description"] = db_desc
            corrected_codes.append(item)
            continue
        
        # Code invalid - check if format is valid but database doesn't have it
        # If format is valid + high confidence, accept anyway (avoid bad auto-corrections)
        format_valid = False
        if system == "ICD10":
            import re
            ICD10_PATTERN = re.compile(r"^[A-TV-Z][0-9][A-Z0-9](?:\.[A-Z0-9]{1,4})?(?:[A-Z0-9]{0,2})?$")
            format_valid = bool(ICD10_PATTERN.match(code.upper()))
        elif system == "CPT":
            import re
            CPT_PATTERN = re.compile(r"^[0-9]{4}[0-9A-Z]$")
            format_valid = bool(CPT_PATTERN.match(code.upper()))
        
        # If format is valid + high confidence, FLAG for review (don't auto-accept)
        # Format validity ≠ code validity in medical billing
        # Human review required for codes not in official database
        if format_valid and confidence >= 0.80:
            item["needs_review"] = True
            item["review_reason"] = (
                f"Code format is valid ({system}: {code}) but not found in official database. "
                f"High confidence ({confidence:.2f}) suggests possible new/emerging code, "
                f"but requires human validation before billing use."
            )
            corrected_codes.append(item)
            flagged_count += 1
            validation_issues.append({
                "code": code,
                "system": system,
                "issue": f"Valid format but not in database (confidence {confidence:.2f})",
            })
            continue
        
        # Check for known CPT code variants (e.g., single vs multi-view imaging)
        # These are valid codes that represent slightly different procedures
        KNOWN_CPT_VARIANTS = {
            "71045": "71046",  # chest X-ray: single view → standard 2 views
            "73610": "73620",  # ankle X-ray: single view → standard 3 views
        }
        
        if system == "CPT" and code in KNOWN_CPT_VARIANTS and confidence >= 0.85:
            # Auto-correct to standard variant for high-confidence cases
            corrected_to = KNOWN_CPT_VARIANTS[code]
            corrected_valid, corrected_reason, corrected_db_desc = validator.validate_code(system, corrected_to)
            if corrected_valid:
                # Update with corrected code
                item["original_code"] = code
                item["code"] = corrected_to
                item["auto_corrected"] = True
                item["confidence_reason"] = (
                    f"Auto-corrected from {code} (single view) to {corrected_to} (standard procedure). "
                    f"{item.get('confidence_reason', '')}"
                )
                if corrected_db_desc:
                    item["db_description"] = corrected_db_desc
                corrected_codes.append(item)
                flagged_count += 1
                validation_issues.append({
                    "code": corrected_to,
                    "system": system,
                    "issue": f"Auto-corrected from {code} to standard variant {corrected_to}",
                })
                continue
        
        # Code invalid AND format is bad OR confidence is low - try auto-correction
        replacement = None
        try:
            if system == "ICD10":
                replacement = validator.find_best_icd_match(evidence)
            elif system == "CPT":
                replacement = validator.find_best_cpt_match(evidence)
        except Exception:
            replacement = None
        
        if replacement and confidence < 0.70:
            # Auto-correct only for low-confidence invalid codes
            repl_valid, repl_reason, repl_db_desc = validator.validate_code(system, replacement)
            item["original_code"] = code
            item["code"] = replacement
            item["auto_corrected"] = True
            item["confidence"] = min(0.9, float(item.get("confidence", 0.6)))
            item["confidence_reason"] = (
                f"Auto-corrected from {code} to {replacement}. {item.get('confidence_reason','')}"
            )
            if repl_db_desc:
                item["db_description"] = repl_db_desc
            corrected_codes.append(item)
            flagged_count += 1
            validation_issues.append({
                "code": replacement,
                "system": system,
                "issue": f"Auto-corrected from {code}",
            })
            continue
        
        # No replacement found - flag for review
        item["needs_review"] = True
        item["review_reason"] = reason or "Unvalidated code"
        flagged_count += 1
        validation_issues.append({
            "code": code,
            "system": system,
            "issue": reason or "Unvalidated code",
        })
        corrected_codes.append(item)
    
    # Additional evidence-based flagging
    corrected_codes, evidence_flags = CodeRetriever.flag_codes_for_review(
        corrected_codes,
        extracted_evidence,
    )
    flagged_count += sum(1 for c in corrected_codes if c.get("needs_review"))
    validation_issues.extend([{"issue": f} for f in evidence_flags])
    
    validation_metadata = {
        "total_codes": len(corrected_codes),
        "flagged_count": flagged_count,
        "auto_corrected_count": sum(1 for c in corrected_codes if c.get("auto_corrected")),
        "needs_review": flagged_count > 0,
        "validation_issues": validation_issues,
    }
    
    return {
        "soap": clean_soap,
        "codes": corrected_codes,
        "extracted_evidence": extracted_evidence,
        "validation_metadata": validation_metadata,
    }
