from django.contrib import admin
from .models import CodingResult, ReviewFeedback


@admin.register(CodingResult)
class CodingResultAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "upload_record", "review_status", "created_at"]
    list_filter = ["review_status", "created_at"]
    search_fields = ["user__username", "upload_record__file_name"]
    readonly_fields = ["created_at", "updated_at", "raw_llm_output"]


@admin.register(ReviewFeedback)
class ReviewFeedbackAdmin(admin.ModelAdmin):
    list_display = ["id", "coding_result", "reviewer", "feedback_type", "created_at"]
    list_filter = ["feedback_type", "created_at"]
    search_fields = ["reviewer__username", "explanation"]
    readonly_fields = ["created_at"]
