from rest_framework import serializers
from .models import CodingResult, ReviewFeedback


class CodingResultSerializer(serializers.ModelSerializer):
    """Shapes a CodingResult for the frontend."""

    upload_record_id = serializers.IntegerField(source="upload_record.id", read_only=True)
    file_url = serializers.CharField(source="upload_record.file_url", read_only=True)
    file_type = serializers.CharField(source="upload_record.file_type", read_only=True)
    file_name = serializers.CharField(source="upload_record.file_name", read_only=True)
    upload_status = serializers.CharField(source="upload_record.status", read_only=True)
    reviewed_by_username = serializers.CharField(source="reviewed_by.username", read_only=True, allow_null=True)

    class Meta:
        model = CodingResult
        fields = [
            "id",
            "upload_record_id",
            "file_url",
            "file_type",
            "file_name",
            "upload_status",
            "soap_note",
            "extracted_evidence",
            "extracted_diagnoses",
            "icd_codes",
            "cpt_codes",
            "summary",
            "confidence",
            "validation_metadata",
            "validation_log",
            "review_status",
            "review_notes",
            "reviewed_by_username",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]


class ReviewFeedbackSerializer(serializers.ModelSerializer):
    """Shapes ReviewFeedback for the frontend."""

    reviewer_username = serializers.CharField(source="reviewer.username", read_only=True)

    class Meta:
        model = ReviewFeedback
        fields = [
            "id",
            "reviewer_username",
            "llm_codes",
            "corrected_codes",
            "feedback_type",
            "explanation",
            "created_at",
        ]


class ReviewSerializer(serializers.Serializer):
    """Validates a human reviewer's decision on a coding result."""

    review_status = serializers.ChoiceField(choices=CodingResult.ReviewStatus.choices)

    # Optional: reviewer can edit the codes during review
    icd_codes = serializers.ListField(child=serializers.DictField(), required=False)
    cpt_codes = serializers.ListField(child=serializers.DictField(), required=False)
    summary = serializers.CharField(required=False, allow_blank=True)
    review_notes = serializers.CharField(required=False, allow_blank=True)
    feedback_type = serializers.ChoiceField(
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
        required=False,
    )
    explanation = serializers.CharField(required=False, allow_blank=True)
