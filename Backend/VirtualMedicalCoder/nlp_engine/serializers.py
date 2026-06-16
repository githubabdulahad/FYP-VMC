from rest_framework import serializers


class AnalyzeInputRequestSerializer(serializers.Serializer):
    raw_text = serializers.CharField(allow_blank=False)
    model = serializers.CharField(required=False, allow_blank=False, max_length=100)
