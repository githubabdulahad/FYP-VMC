from django.urls import path
from .views import ReportDetailView , ReportListView

urlpatterns = [
  path("", ReportListView.as_view(), name="list-all"),
  path("<int:result_id>/", ReportDetailView.as_view(), name="detail"),
]