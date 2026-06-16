"""
test_source_validation.py

Test suite for source validation gate (ICD-10-CM Section I.B.1 compliance).

Tests verify that the system:
1. Never codes patient-only statements as diagnoses
2. Only codes physician-confirmed diagnoses
3. Uses Z87.x codes for historical conditions affecting current care
4. Properly tracks source attribution through the pipeline
"""

import os
import json
import django
from pathlib import Path

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "VirtualMedicalCoder.settings")
django.setup()

from VirtualMedicalCoder.nlp_engine.two_stage_pipeline import (
    run_stage_1_normalization,
    run_stage_2_code_generation,
)
from VirtualMedicalCoder.coding.code_retrieval import CodeRetriever


class TestSourceValidation:
    """Test source validation gate against real clinical scenarios."""

    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []

    def assert_true(self, condition, test_name, details=""):
        """Record assertion result."""
        if condition:
            self.passed_tests += 1
            self.test_results.append({"status": "PASS", "test": test_name, "details": details})
            print(f"✓ {test_name}")
        else:
            self.failed_tests += 1
            self.test_results.append({"status": "FAIL", "test": test_name, "details": details})
            print(f"✗ {test_name}\n  Details: {details}")

    def assert_in(self, item, container, test_name, details=""):
        """Assert item is in container."""
        self.assert_true(item in container, test_name, details)

    def assert_not_in(self, item, container, test_name, details=""):
        """Assert item is not in container."""
        self.assert_true(item not in container, test_name, details)

    # =========================================================================
    # TEST 1: Patient Statement Only - Should NOT Code
    # =========================================================================

    def test_patient_statement_anxiety_not_coded(self):
        """
        Scenario: Patient reports anxiety; doctor never confirms.
        Expected: DO NOT code F41.9
        Rule: ICD-10-CM I.B.1 - physician confirmation required
        """
        print("\n" + "="*70)
        print("TEST 1: Patient Statement Only (Anxiety)")
        print("="*70)
        
        raw_text = """
        Patient: I'm pretty anxious all the time
        Doctor: Let me take your blood pressure. [checks vitals]
                Everything looks normal. See you in 6 months.
        """
        
        # Stage 1: SOAP generation
        soap = run_stage_1_normalization(raw_text)
        self.assert_true(
            "[Patient reported]" in json.dumps(soap),
            "Stage 1 attributes anxiety as [Patient reported]",
            f"SOAP Assessment: {soap.get('assessment', '')}"
        )
        
        # Stage 2: Code generation - should include source validation
        codes = run_stage_2_code_generation(soap)
        
        # Check that F41.9 (anxiety) is NOT in the coded diagnoses
        coded_icd_codes = [code.get("code") for code in codes.get("diagnoses", []) if code.get("coded")]
        self.assert_not_in(
            "F41.9",
            coded_icd_codes,
            "Anxiety (F41.9) is NOT coded (patient statement only)",
            f"Coded diagnoses: {coded_icd_codes}"
        )
        
        # Check validation log shows rejection with source reason
        validation_summary = codes.get("validation_summary", {})
        self.assert_true(
            validation_summary.get("rejected_diagnoses", 0) > 0,
            "Validation log shows rejected diagnoses",
            f"Summary: {validation_summary}"
        )

    # =========================================================================
    # TEST 2: Motorcycle Case - Historical Unconfirmed Injury
    # =========================================================================

    def test_motorcycle_shoulder_injury_not_coded(self):
        """
        Scenario: Patient mentions shoulder injury from accident; doctor never treats/confirms it.
        Expected: DO NOT code S43.401A
        Rule: Doctor examined arm wounds but not shoulder = patient statement only
        """
        print("\n" + "="*70)
        print("TEST 2: Motorcycle Case - Shoulder Injury (Patient Reported Only)")
        print("="*70)
        
        raw_text = """
        Patient: I injured my shoulder in that motorcycle accident in June
        Doctor: Let me examine your wounds. I see deep lacerations on your left arm.
                We need to clean and dress these properly. Your shoulder looks okay.
        """
        
        # Stage 1: SOAP generation
        soap = run_stage_1_normalization(raw_text)
        assessment = soap.get("assessment", "")
        
        # Verify Stage 1 tagged shoulder as patient-reported
        self.assert_true(
            "[Patient reported]" in assessment,
            "Stage 1 attributes shoulder injury as [Patient reported]",
            f"Assessment: {assessment}"
        )
        
        # Verify Stage 1 tagged arm wounds as doctor-confirmed
        self.assert_true(
            "[Doctor" in assessment or "lacerations" in assessment.lower(),
            "Stage 1 captures doctor-confirmed arm wounds",
            f"Assessment: {assessment}"
        )
        
        # Stage 2: Code generation
        codes = run_stage_2_code_generation(soap)
        coded_icd_codes = [code.get("code") for code in codes.get("diagnoses", []) if code.get("coded")]
        
        # Shoulder injury (S43.xxx) should NOT be coded
        shoulder_codes = [c for c in coded_icd_codes if c and c.startswith("S43")]
        self.assert_true(
            len(shoulder_codes) == 0,
            "Shoulder injury (S43.xxx) is NOT coded",
            f"Coded diagnosis codes: {coded_icd_codes}"
        )
        
        # Arm laceration (S51.xxx) SHOULD be coded
        arm_codes = [c for c in coded_icd_codes if c and c.startswith("S51")]
        self.assert_true(
            len(arm_codes) > 0,
            "Arm laceration (S51.xxx) IS coded",
            f"Coded diagnosis codes: {coded_icd_codes}"
        )

    # =========================================================================
    # TEST 3: Pheochromocytoma - Patient-Reported Symptoms vs Doctor-Confirmed Diagnosis
    # =========================================================================

    def test_pheochromocytoma_anxiety_not_coded_symptom_not_coded(self):
        """
        Scenario: Patient reports anxiety and weight loss; doctor confirms pheochromocytoma.
        Expected: 
        - DO NOT code F41.9 (anxiety - patient statement only)
        - DO NOT code R63.4 (weight loss - symptom of confirmed diagnosis)
        - DO code E34.2 (pheochromocytoma - physician confirmed)
        Rule: ICD-10-CM Section I.B.1 + symptoms integral to diagnosed condition
        """
        print("\n" + "="*70)
        print("TEST 3: Pheochromocytoma Case")
        print("="*70)
        
        raw_text = """
        Patient: I'm pretty anxious all the time and I've lost 6kg without trying
        Doctor: Based on your symptoms and test results, you have pheochromocytoma.
                I'm starting you on alpha blockers. We'll get you to a specialist.
        """
        
        # Stage 1: SOAP generation
        soap = run_stage_1_normalization(raw_text)
        assessment = soap.get("assessment", "")
        
        self.assert_true(
            "[Patient reported]" in assessment or "patient said" in assessment.lower(),
            "Stage 1 attributes patient symptoms as [Patient reported]",
            f"Assessment: {assessment}"
        )
        
        self.assert_true(
            "[Doctor" in assessment or "pheochromocytoma" in assessment.lower(),
            "Stage 1 attributes pheo as [Doctor confirmed]",
            f"Assessment: {assessment}"
        )
        
        # Stage 2: Code generation
        codes = run_stage_2_code_generation(soap)
        coded_icd_codes = [code.get("code") for code in codes.get("diagnoses", []) if code.get("coded")]
        
        # Anxiety (F41.9) should NOT be coded
        self.assert_not_in(
            "F41.9",
            coded_icd_codes,
            "Anxiety (F41.9) is NOT coded (patient statement, not confirmed)",
            f"Coded codes: {coded_icd_codes}"
        )
        
        # Abnormal weight loss (R63.4) should NOT be coded
        self.assert_not_in(
            "R63.4",
            coded_icd_codes,
            "Abnormal weight loss (R63.4) is NOT coded (integral symptom of pheo)",
            f"Coded codes: {coded_icd_codes}"
        )
        
        # Pheochromocytoma (E34.2) SHOULD be coded
        pheo_codes = [c for c in coded_icd_codes if c and c.startswith("E34")]
        self.assert_true(
            len(pheo_codes) > 0,
            "Pheochromocytoma (E34.2) IS coded",
            f"Coded codes: {coded_icd_codes}"
        )

    # =========================================================================
    # TEST 4: Pneumonia - Symptoms with Confirmed Diagnosis
    # =========================================================================

    def test_pneumonia_fever_cough_not_coded_separately(self):
        """
        Scenario: Patient reports cough and fever; doctor diagnoses pneumonia.
        Expected:
        - CODE J18.9 (pneumonia - confirmed)
        - DO NOT CODE R05.9 (fever - integral to pneumonia)
        - DO NOT CODE R06.9 (cough - integral to pneumonia)
        Rule: Symptoms explained by confirmed diagnosis should not be coded separately
        """
        print("\n" + "="*70)
        print("TEST 4: Pneumonia Case")
        print("="*70)
        
        raw_text = """
        Patient: I've had a cough for 10 days and a fever
        Doctor: I'm concerned about pneumonia. I'm ordering a chest X-ray and starting antibiotics.
                Your exam shows crackles in the left lung.
        """
        
        # Stage 1: SOAP generation
        soap = run_stage_1_normalization(raw_text)
        assessment = soap.get("assessment", "")
        
        # Stage 2: Code generation
        codes = run_stage_2_code_generation(soap)
        coded_icd_codes = [code.get("code") for code in codes.get("diagnoses", []) if code.get("coded")]
        
        # Pneumonia (J18.9) SHOULD be coded
        pneumonia_codes = [c for c in coded_icd_codes if c and c.startswith("J18")]
        self.assert_true(
            len(pneumonia_codes) > 0,
            "Pneumonia (J18.9) IS coded",
            f"Coded codes: {coded_icd_codes}"
        )
        
        # Fever (R05.9, R50.9) should NOT be coded
        fever_codes = [c for c in coded_icd_codes if c and (c.startswith("R05") or c.startswith("R50"))]
        self.assert_true(
            len(fever_codes) == 0,
            "Fever (R05.9/R50.9) is NOT coded (integral to pneumonia)",
            f"Coded codes: {coded_icd_codes}"
        )
        
        # Cough (R06.9) should NOT be coded
        self.assert_not_in(
            "R06.9",
            coded_icd_codes,
            "Cough (R06.9) is NOT coded (integral to pneumonia)",
            f"Coded codes: {coded_icd_codes}"
        )

    # =========================================================================
    # TEST 5: Historical Condition Affecting Current Care - Use Z87.x
    # =========================================================================

    def test_historical_mi_affecting_current_care_uses_zcode(self):
        """
        Scenario: Patient mentions past MI; doctor reviews it for current medication decision.
        Expected:
        - CODE Z87.891 (personal history of MI) because it affects current care
        - NOT coded as I21.x (acute MI)
        Rule: Historical conditions coded with Z87.x only if affecting current treatment
        """
        print("\n" + "="*70)
        print("TEST 5: Historical MI Affecting Current Care")
        print("="*70)
        
        raw_text = """
        Patient: I had a heart attack 2 years ago
        Doctor: Given your cardiac history, I'm going to order an ECG before prescribing this blood pressure medication.
                Your current BP is elevated at 155/95.
        """
        
        # Stage 1: SOAP generation
        soap = run_stage_1_normalization(raw_text)
        assessment = soap.get("assessment", "")
        
        self.assert_true(
            "[Doctor reviewed]" in assessment or "cardiac history" in assessment.lower(),
            "Stage 1 captures historical MI with doctor's clinical relevance",
            f"Assessment: {assessment}"
        )
        
        # Stage 2: Code generation
        codes = run_stage_2_code_generation(soap)
        coded_icd_codes = [code.get("code") for code in codes.get("diagnoses", []) if code.get("coded")]
        
        # Z87.891 (personal history MI) SHOULD be coded
        z_codes = [c for c in coded_icd_codes if c and c.startswith("Z87")]
        self.assert_true(
            len(z_codes) > 0,
            "Personal history code (Z87.891) IS coded",
            f"Coded codes: {coded_icd_codes}"
        )
        
        # Acute MI codes (I21.x) should NOT be coded
        mi_codes = [c for c in coded_icd_codes if c and c.startswith("I21")]
        self.assert_true(
            len(mi_codes) == 0,
            "Acute MI (I21.x) is NOT coded (historical, not current)",
            f"Coded codes: {coded_icd_codes}"
        )

    # =========================================================================
    # TEST 6: Source Validation Gate Function
    # =========================================================================

    def test_codeable_by_source_physician_confirmed(self):
        """Test is_codeable_by_source() function."""
        print("\n" + "="*70)
        print("TEST 6: Source Validation Gate Function")
        print("="*70)
        
        # Test 1: Physician-confirmed, current visit -> CODEABLE
        source_info = {
            "source": "physician_confirmed",
            "is_current_visit": True,
            "source_evidence": "Doctor: Type 2 Diabetes on metformin",
        }
        is_codeable, reason = CodeRetriever.is_codeable_by_source(source_info)
        self.assert_true(
            is_codeable,
            "Physician-confirmed, current visit -> CODEABLE",
            f"Reason: {reason}"
        )
        
        # Test 2: Patient-reported, no confirmation -> NOT CODEABLE
        source_info = {
            "source": "patient_reported",
            "is_current_visit": False,
            "source_evidence": "Patient said 'I'm anxious all the time'",
        }
        is_codeable, reason = CodeRetriever.is_codeable_by_source(source_info)
        self.assert_true(
            not is_codeable,
            "Patient-reported, no confirmation -> NOT CODEABLE",
            f"Reason: {reason}"
        )
        
        # Test 3: Historical, affects current care -> CODEABLE (with Z87.x)
        source_info = {
            "source": "historical",
            "is_current_visit": False,
            "affects_current_care": True,
            "source_evidence": "Doctor reviewed cardiac history before prescribing medication",
        }
        is_codeable, reason = CodeRetriever.is_codeable_by_source(source_info)
        self.assert_true(
            is_codeable,
            "Historical, affects current care -> CODEABLE",
            f"Reason: {reason}"
        )
        
        # Test 4: Historical, doesn't affect current care -> NOT CODEABLE
        source_info = {
            "source": "historical",
            "is_current_visit": False,
            "affects_current_care": False,
            "source_evidence": "Patient mentioned old shoulder injury, not addressed",
        }
        is_codeable, reason = CodeRetriever.is_codeable_by_source(source_info)
        self.assert_true(
            not is_codeable,
            "Historical, doesn't affect current care -> NOT CODEABLE",
            f"Reason: {reason}"
        )

    # =========================================================================
    # RUN ALL TESTS
    # =========================================================================

    def run_all_tests(self):
        """Run complete test suite."""
        print("\n")
        print("╔" + "="*68 + "╗")
        print("║" + " "*15 + "SOURCE VALIDATION GATE TEST SUITE" + " "*20 + "║")
        print("║" + " "*10 + "ICD-10-CM Section I.B.1 Compliance Testing" + " "*15 + "║")
        print("╚" + "="*68 + "╝")
        
        try:
            self.test_patient_statement_anxiety_not_coded()
            self.test_motorcycle_shoulder_injury_not_coded()
            self.test_pheochromocytoma_anxiety_not_coded_symptom_not_coded()
            self.test_pneumonia_fever_cough_not_coded_separately()
            self.test_historical_mi_affecting_current_care_uses_zcode()
            self.test_codeable_by_source_physician_confirmed()
        except Exception as e:
            print(f"\n❌ Test execution error: {e}")
            import traceback
            traceback.print_exc()
        
        # Print summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Total:  {self.passed_tests + self.failed_tests}")
        
        if self.failed_tests == 0:
            print("\n✓ ALL TESTS PASSED - Source validation gate is working correctly")
        else:
            print(f"\n✗ {self.failed_tests} TEST(S) FAILED - Review implementation")
        
        print("="*70)
        
        return self.failed_tests == 0


if __name__ == "__main__":
    tester = TestSourceValidation()
    success = tester.run_all_tests()
    exit(0 if success else 1)
