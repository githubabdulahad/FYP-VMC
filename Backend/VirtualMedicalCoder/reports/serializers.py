from rest_framework import serializers


class ReportSerializer(serializers.Serializer):
    """
    Shapes a full report — combines coding result data into one clean response.
    This is what the frontend renders on the 'Results' page.
    """

    id = serializers.IntegerField(source="coding_result.id")
    file_name = serializers.CharField(source="upload_record.file_name")
    file_type = serializers.CharField(source="upload_record.file_type")
    file_url = serializers.CharField(source="upload_record.file_url")
    extracted_text = serializers.CharField(source="upload_record.extracted_text")
    soap_note = serializers.JSONField(source="coding_result.soap_note")
    icd_codes = serializers.JSONField(source="coding_result.icd_codes")
    cpt_codes = serializers.JSONField(source="coding_result.cpt_codes")
    summary = serializers.CharField(source="coding_result.summary")
    confidence = serializers.FloatField(source="coding_result.confidence")
    review_status = serializers.CharField(source="coding_result.review_status")
    created_at = serializers.DateTimeField(source="upload_record.created_at")


class _FlatRecord:
    """
    A flat object that combines UploadRecord + CodingResult for the serializer.
    The serializer uses source= to pull from both sub-objects.
    """
    def __init__(self, upload_record, coding_result):
        self.upload_record = upload_record
        self.coding_result = coding_result
