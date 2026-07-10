from django.urls import path
from .views import (
    FileUploadView, UploadStatusView,
    PartnerSubmitDocumentView, PartnerDocumentStatusView,
)

urlpatterns = [
  path("upload/", FileUploadView.as_view(), name="file-upload"),
  path("upload/<int:record_id>/", UploadStatusView.as_view(), name="upload-status"),

  # Partner API (organization API key auth, not browser session)
  path("partner/documents/", PartnerSubmitDocumentView.as_view(), name="partner-document-submit"),
  path("partner/documents/<int:record_id>/", PartnerDocumentStatusView.as_view(), name="partner-document-status"),
]