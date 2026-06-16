from django.urls import path
from .views import (
    CodingResultDetailView,
    CodingReviewView,
    CodingResultListView,
    ReviewFeedbackListView,
    CodeAlternativesView,
    DeleteCodeView,
)

urlpatterns = [
    path("", CodingResultListView.as_view(), name="list-all"),
    path("<int:result_id>/", CodingResultDetailView.as_view(), name="detail"),
    path("<int:result_id>/review/", CodingReviewView.as_view(), name="review-codes"),
    path("<int:result_id>/feedback/", ReviewFeedbackListView.as_view(), name="feedback-history"),
    path("<int:result_id>/alternatives/", CodeAlternativesView.as_view(), name="code-alternatives"),
    path("<int:result_id>/delete/", DeleteCodeView.as_view(), name="delete-code"),
    path("<int:result_id>/code/", DeleteCodeView.as_view(), name="delete-code"),
]