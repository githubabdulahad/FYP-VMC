"""
coding/models.py

Stores the structured output from the LLM — SOAP note + ICD/CPT codes.
Each CodingResult is linked to one UploadRecord.
"""

from django.contrib.auth import get_user_model
from django.db import models

from ingestion.models import UploadRecord

User = get_user_model()


class CodingResult(models.Model):
    """
    The final output of the pipeline:
    upload → extract text → LLM → this model.
    
    Stores:
    - Normalized clinical summary (SOAP)
    - Structured evidence (extracted diagnoses, procedures, findings)
    - Generated codes (ICD-10, CPT) with confidence and provenance
    - Review status and audit trail for human review workflow
    """

    upload_record  = models.OneToOneField(
        UploadRecord,
        on_delete=models.CASCADE,
        related_name="coding_result",
    )
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name="coding_results")

    # SOAP note stored as a JSON object
    # e.g. {"subjective": "...", "objective": "...", "assessment": "...", "plan": "..."}
    soap_note      = models.JSONField(default=dict)

    # STRUCTURED EVIDENCE — extracted facts from clinical text
    # e.g. {
    #   "diagnoses": [{"condition": "Type 2 Diabetes", "acuity": "chronic", "laterality": null}],
    #   "procedures": [{"name": "CT scan abdomen", "approach": "imaging"}],
    #   "symptoms": ["fatigue", "polyuria"],
    #   "findings": [{"type": "vital", "name": "BP", "value": "140/90"}]
    # }
    extracted_evidence = models.JSONField(default=dict)

    # EXTRACTED DIAGNOSES WITH SOURCE TRACKING (NEW - ICD-10-CM I.B.1 compliance)
    # Stores diagnoses with source attribution and coding decision
    extracted_diagnoses = models.JSONField(
        default=list,
        help_text="Diagnoses with source tracking and coding decisions (ICD-10-CM Section I.B.1)"
    )

    # Lists of code objects with full metadata
    # e.g. [{"code": "E11.9", "description": "...", "confidence": 0.95, "evidence_text": "...", "flagged": false}]
    icd_codes      = models.JSONField(default=list)
    cpt_codes      = models.JSONField(default=list)
    snomed_codes   = models.JSONField(default=list)

    summary        = models.TextField(blank=True)
    confidence     = models.FloatField(null=True, blank=True)  # Overall LLM confidence score

    # Raw LLM output stored for debugging and audit trail
    raw_llm_output = models.TextField(blank=True)

    # VALIDATION METADATA — tracks auto-corrections and flags for review
    # e.g. {
    #   "total_codes": 5,
    #   "flagged_count": 2,
    #   "auto_corrected_count": 1,
    #   "needs_review": true,
    #   "validation_issues": [...]
    # }
    validation_metadata = models.JSONField(default=dict)

    # VALIDATION LOG — tracks source validation gate decisions per diagnosis (NEW)
    validation_log = models.JSONField(
        default=dict,
        help_text="Source validation gate decisions and reasoning per diagnosis"
    )

    # Review status — set by a human reviewer
    class ReviewStatus(models.TextChoices):
        PENDING  = "pending",  "Pending Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        REVISED  = "revised",  "Revised"

    review_status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )

    # Review notes from the reviewer
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_coding_results",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CodingResult #{self.id} | {self.upload_record} | {self.review_status}"


class ReviewFeedback(models.Model):
    """
    Tracks reviewer corrections for continuous learning.
    Every time a reviewer changes codes, marks something for revision, etc.,
    we record it here to identify patterns and improve the LLM pipeline.
    """

    coding_result = models.ForeignKey(
        CodingResult,
        on_delete=models.CASCADE,
        related_name="review_feedback",
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="coding_feedback",
    )

    # What the LLM generated
    llm_codes = models.JSONField(default=list)
    
    # What the reviewer changed it to
    corrected_codes = models.JSONField(default=list)

    # Why the correction was made
    feedback_type = models.CharField(
        max_length=50,
        choices=[
            ("missing_code", "Missing Code Added"),
            ("incorrect_code", "Code Corrected"),
            ("specificity", "Increased Specificity"),
            ("completeness", "Enhanced Completeness"),
            ("conflict_resolved", "Conflicting Code Removed"),
            # NEW: Source validation feedback types (ICD-10-CM Section I.B.1)
            ("source_misidentified", "Source Misidentified - Not Physician Confirmed"),
            ("unverified_condition_coded", "Unverified Condition Coded - Patient Statement Only"),
            ("historical_incorrectly_coded", "Historical Condition Coded as Current"),
            ("physician_confirmed_not_coded", "Physician Confirmed But Not Coded"),
            ("patient_reported_coded", "Patient-Only Statement Coded - ICD-10-CM Violation"),
            ("other", "Other"),
        ],
        default="other",
    )
    
    # Explanation from reviewer
    explanation = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback on CodingResult {self.coding_result.id} by {self.reviewer}"