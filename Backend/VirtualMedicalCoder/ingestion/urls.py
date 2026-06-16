from django.urls import path
from .views import FileUploadView , UploadStatusView

urlpatterns = [
  path("upload/", FileUploadView.as_view(), name="file-upload"),
  path("upload/<int:record_id>/", UploadStatusView.as_view(), name="upload-status"),
]