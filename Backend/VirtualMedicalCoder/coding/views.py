"""
coding/views.py

Real API endpoints (replaces your placeholder views).

  GET  /api/coding/                      — list all coding results for the logged-in user
  GET  /api/coding/<id>/                 — get one result
  POST /api/coding/<id>/review/          — approve, reject, or revise a result
  GET  /api/coding/<id>/feedback/        — get review feedback history
  POST /api/coding/<id>/alternatives/    — get alternative code suggestions
"""

from datetime import datetime

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import JWTCookieAuthentication
from VirtualMedicalCoder.swagger import BAD_REQUEST, NOT_FOUND, UNAUTHORIZED
from .models import CodingResult, ReviewFeedback
from .serializers import CodingResultSerializer, ReviewSerializer, ReviewFeedbackSerializer
from .code_retrieval import CodeRetriever

class CodingResultListView(APIView):
    """
    GET /api/coding/
    Returns all coding results for the currently logged-in user.
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes     = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="List coding results for current user",
        responses={200: openapi.Response("List of coding results"), 401: UNAUTHORIZED},
        tags=["Coding"],
    )
    def get(self, request):
        results = (
            CodingResult.objects
            .filter(user=request.user)
            .select_related("upload_record")
            .order_by("-created_at")
        )
        serializer = CodingResultSerializer(results, many=True)
        return Response(serializer.data)


class CodingResultDetailView(APIView):
    """
    GET /api/coding/<id>/
    Returns one specific coding result (must belong to the current user).
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes     = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get one coding result",
        manual_parameters=[
            openapi.Parameter("result_id", openapi.IN_PATH, type=openapi.TYPE_INTEGER, required=True),
        ],
        responses={200: openapi.Response("Coding result detail"), 401: UNAUTHORIZED, 404: NOT_FOUND},
        tags=["Coding"],
    )
    def get(self, request, result_id):
        try:
            result = CodingResult.objects.select_related("upload_record").get(
                id=result_id,
                user=request.user,
            )
        except CodingResult.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(CodingResultSerializer(result).data)


class CodingReviewView(APIView):
    """
    POST /api/coding/<id>/review/

    A human reviewer approves, rejects, or revises the AI-generated codes.
    They can also correct ICD/CPT codes or the summary during this step.

    Body:
    {
        "review_status": "approved" | "rejected" | "revised",
        "icd_codes": [...],        (optional — only if revising)
        "cpt_codes": [...],        (optional — only if revising)
        "summary": "...",          (optional — only if revising)
        "review_notes": "...",     (optional)
        "feedback_type": "...",    (optional — if codes were corrected)
        "explanation": "..."       (optional — if codes were corrected)
    }
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes     = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Human review: approve, reject, or revise codes",
        manual_parameters=[
            openapi.Parameter("result_id", openapi.IN_PATH, type=openapi.TYPE_INTEGER, required=True),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["review_status"],
            properties={
                "review_status": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["approved", "rejected", "revised"],
                ),
                "icd_codes": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                "cpt_codes": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                "summary": openapi.Schema(type=openapi.TYPE_STRING),
                "review_notes": openapi.Schema(type=openapi.TYPE_STRING),
                "feedback_type": openapi.Schema(type=openapi.TYPE_STRING),
                "explanation": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: openapi.Response("Updated coding result"), 400: BAD_REQUEST, 401: UNAUTHORIZED, 404: NOT_FOUND},
        tags=["Coding"],
    )
    def post(self, request, result_id):
        try:
            result = CodingResult.objects.get(id=result_id, user=request.user)
        except CodingResult.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Track if codes changed for feedback
        codes_changed = False
        original_icd = result.icd_codes
        original_cpt = result.cpt_codes

        # Apply reviewer's decision
        result.review_status = data["review_status"]
        result.reviewed_by = request.user
        result.reviewed_at = datetime.now()

        # Apply optional corrections
        if "icd_codes" in data:
            result.icd_codes = data["icd_codes"]
            codes_changed = codes_changed or (data["icd_codes"] != original_icd)

        if "cpt_codes" in data:
            result.cpt_codes = data["cpt_codes"]
            codes_changed = codes_changed or (data["cpt_codes"] != original_cpt)

        if "summary" in data:
            result.summary = data["summary"]

        if "review_notes" in data:
            result.review_notes = data["review_notes"]

        result.save()

        # Create feedback record if codes were corrected
        if codes_changed and data.get("feedback_type"):
            ReviewFeedback.objects.create(
                coding_result=result,
                reviewer=request.user,
                llm_codes=original_icd + original_cpt,
                corrected_codes=result.icd_codes + result.cpt_codes,
                feedback_type=data.get("feedback_type", "other"),
                explanation=data.get("explanation", ""),
            )

        return Response(
            CodingResultSerializer(result).data,
            status=status.HTTP_200_OK,
        )


class ReviewFeedbackListView(APIView):
    """
    GET /api/coding/<id>/feedback/
    Returns all review feedback for a coding result (for learning/improvement tracking).
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes     = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Review feedback history for a coding result",
        manual_parameters=[
            openapi.Parameter("result_id", openapi.IN_PATH, type=openapi.TYPE_INTEGER, required=True),
        ],
        responses={200: openapi.Response("Feedback list"), 401: UNAUTHORIZED, 404: NOT_FOUND},
        tags=["Coding"],
    )
    def get(self, request, result_id):
        try:
            result = CodingResult.objects.get(id=result_id, user=request.user)
        except CodingResult.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        feedback = result.review_feedback.all().order_by("-created_at")
        serializer = ReviewFeedbackSerializer(feedback, many=True)
        return Response(serializer.data)


class CodeAlternativesView(APIView):
    """
    POST /api/coding/<id>/alternatives/

    Get alternative code suggestions for a diagnosis or procedure based on evidence.
    Useful during review to suggest corrections.

    Body:
    {
        "system": "ICD10" | "CPT",
        "evidence_text": "Type 2 diabetes with complications"
    }

    Returns:
    {
        "candidates": [
            {"code": "E11.9", "description": "...", "score": 0.85},
            ...
        ]
    }
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes     = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Suggest alternative ICD-10 or CPT codes from evidence text",
        manual_parameters=[
            openapi.Parameter("result_id", openapi.IN_PATH, type=openapi.TYPE_INTEGER, required=True),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["system", "evidence_text"],
            properties={
                "system": openapi.Schema(type=openapi.TYPE_STRING, enum=["ICD10", "CPT"]),
                "evidence_text": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: openapi.Response("Ranked code candidates"), 400: BAD_REQUEST, 401: UNAUTHORIZED, 404: NOT_FOUND},
        tags=["Coding"],
    )
    def post(self, request, result_id):
        try:
            result = CodingResult.objects.get(id=result_id, user=request.user)
        except CodingResult.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        system = request.data.get("system", "").upper()
        evidence_text = request.data.get("evidence_text", "").strip()

        if not system or not evidence_text:
            return Response(
                {"error": "Missing 'system' or 'evidence_text'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if system == "ICD10":
            candidates = CodeRetriever.retrieve_icd_candidates(evidence_text, top_k=10)
        elif system == "CPT":
            candidates = CodeRetriever.retrieve_cpt_candidates(evidence_text, top_k=10)
        else:
            return Response(
                {"error": "Invalid system. Must be 'ICD10' or 'CPT'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"candidates": candidates})


class DeleteCodeView(APIView):
    """
    DELETE /api/coding/<result_id>/code/
    Deletes a single ICD or CPT code from a coding result.
    Body:
    {
        "code": "E11.9",
        "type": "icd"
    }
    """
    authentication_classes = [JWTCookieAuthentication]
    permission_classes     = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Delete a code from a coding result",
        manual_parameters=[
            openapi.Parameter("result_id", openapi.IN_PATH, type=openapi.TYPE_INTEGER, required=True),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "code": openapi.Schema(type=openapi.TYPE_STRING, description="The code to delete"),
                "type": openapi.Schema(type=openapi.TYPE_STRING, description="The type of code (icd or cpt)"),
            },
            required=["code", "type"]
        ),
        responses={200: openapi.Response("Updated coding result"), 400: BAD_REQUEST, 401: UNAUTHORIZED, 404: NOT_FOUND},
        tags=["Coding"],
    )
    def delete(self, request, result_id):
        try:
            result = CodingResult.objects.get(id=result_id, user=request.user)
        except CodingResult.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        code_to_delete = request.data.get("code")
        code_type = request.data.get("type")

        if not code_to_delete or not code_type:
            return Response({"error": "Code and type are required."}, status=status.HTTP_400_BAD_REQUEST)

        if code_type not in ["icd", "cpt"]:
            return Response({"error": "Invalid code type."}, status=status.HTTP_400_BAD_REQUEST)

        if code_type == "icd":
            result.icd_codes = [c for c in result.icd_codes if c.get("code") != code_to_delete]
        else: #cpt
            result.cpt_codes = [c for c in result.cpt_codes if c.get("code") != code_to_delete]

        result.save()
        serializer = CodingResultSerializer(result)
        return Response(serializer.data)