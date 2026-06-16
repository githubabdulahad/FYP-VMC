from rest_framework import serializers
from .models import UploadRecord    
# ingestion/serializers.py

class UploadRecordCreateSerializer(serializers.Serializer):
    file_url  = serializers.URLField(required=False, allow_blank=True)
    file_type = serializers.ChoiceField(choices=UploadRecord.FileType.choices)
    file_name = serializers.CharField(max_length=255, required=False, default="")
    raw_text  = serializers.CharField(required=False, allow_blank=True)  # ← ADD THIS

    def validate(self, data):
        file_type = data.get("file_type")
        file_url  = data.get("file_url", "")
        raw_text  = data.get("raw_text", "")

        # If it's a raw_text submission, text must be provided
        if file_type == "raw_text" and not raw_text.strip():
            raise serializers.ValidationError(
                {"raw_text": "Please enter some clinical text."}
            )

        # If it's a file submission, URL must be provided
        if file_type != "raw_text" and not file_url:
            raise serializers.ValidationError(
                {"file_url": "A file URL is required for this input type."}
            )

        return data
 
class UploadRecordResponseSerializer(serializers.ModelSerializer):
    """
    Shapes the UploadRecord that gets returned to the frontend.
    Used both in the create response and when polling for status.
    """
 
    class Meta:
        model  = UploadRecord
        fields = [
            "id",
            "file_url",
            "file_type",
            "file_name",
            "status",
            "extracted_text",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
 