from django.urls import path

from .views import AnalyzeInputRecordView

urlpatterns = [
    path("analyze/", AnalyzeInputRecordView.as_view(), name="nlp-analyze"),
]
