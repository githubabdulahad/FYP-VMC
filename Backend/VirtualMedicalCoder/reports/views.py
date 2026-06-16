"""
reports/views.py

Replaces your placeholder views with real report generation endpoints.

  GET /api/reports/                  — list reports for the user
  GET /api/reports/<coding_result_id>/ — get a full report for one coding result
"""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import JWTCookieAuthentication
from VirtualMedicalCoder.swagger import NOT_FOUND, UNAUTHORIZED
from coding.models import CodingResult
from .serializers import ReportSerializer, _FlatRecord


class ReportListView(APIView):
    """
    GET /api/reports/
    Lists all completed reports (coding results that are approved or revised) for the user.
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes     = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List verified reports (approved or revised)",
        responses={200: openapi.Response("Report summaries"), 401: UNAUTHORIZED},
        tags=["Reports"],
    )
    def get(self, request):
        results = (
            CodingResult.objects
            .filter(
                user=request.user,
                review_status__in=[
                    CodingResult.ReviewStatus.APPROVED,
                    CodingResult.ReviewStatus.REVISED,
                ],
            )
            .select_related("upload_record")
            .order_by("-created_at")
        )

        flat_records = [
            _FlatRecord(r.upload_record, r) for r in results
        ]

        serializer = ReportSerializer(flat_records, many=True)
        return Response(serializer.data)


class ReportDetailView(APIView):
    """
    GET /api/reports/<coding_result_id>/

    Returns the full report for one completed coding result.
    Includes: extracted text, SOAP note, ICD codes, CPT codes, summary.
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes     = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get full verified report for download / display",
        manual_parameters=[
            openapi.Parameter("result_id", openapi.IN_PATH, type=openapi.TYPE_INTEGER, required=True),
        ],
        responses={200: openapi.Response("Full report payload"), 401: UNAUTHORIZED, 404: NOT_FOUND},
        tags=["Reports"],
    )
    def get(self, request, result_id):
        try:
            coding_result = CodingResult.objects.select_related("upload_record").get(
                id=result_id,
                user=request.user,
            )
        except CodingResult.DoesNotExist:
            return Response({"error": "Report not found."}, status=status.HTTP_404_NOT_FOUND)

        flat = _FlatRecord(coding_result.upload_record, coding_result)
        serializer = ReportSerializer(flat)
        return Response(serializer.data)