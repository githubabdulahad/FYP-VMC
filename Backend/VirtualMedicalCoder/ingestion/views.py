"""
ingestion/views.py
 
Two endpoints:
  POST /api/ingestion/upload/      — receive file URL, trigger processing
  GET  /api/ingestion/upload/<id>/ — poll for processing status
"""
 
import logging
 
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
 
from accounts.authentication import JWTCookieAuthentication
from VirtualMedicalCoder.swagger import BAD_REQUEST, NOT_FOUND, UNAUTHORIZED
 
from .models import UploadRecord
from .serializers import UploadRecordCreateSerializer, UploadRecordResponseSerializer
from .tasks import process_upload_async
 
logger = logging.getLogger(__name__)
 
 
class FileUploadView(APIView):
    """
    POST /api/ingestion/upload/
 
    The frontend has already uploaded the file to cloud storage (Cloudinary / S3 / Supabase).
    It now sends us:
        {
            "file_url":  "https://...",
            "file_type": "pdf" | "image" | "audio",
            "file_name": "patient_notes.pdf"
        }
 
    We:
        1. Validate the payload.
        2. Create an UploadRecord in the DB.
        3. Queue background extraction + NLP work with Celery.
        4. Return immediately with HTTP 202 so the frontend can poll status.
    """
 
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]
 
    @swagger_auto_schema(
        operation_summary="Submit clinical input for processing",
        operation_description=(
            "For files: upload to Cloudinary/S3 first, then send `file_url`. "
            "For direct text: set `file_type` to `raw_text` and provide `raw_text`. "
            "Returns 202; poll GET upload/<id>/ for pipeline status."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["file_type"],
            properties={
                "file_url": openapi.Schema(type=openapi.TYPE_STRING, format="uri"),
                "file_type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["pdf", "image", "audio", "raw_text"],
                ),
                "file_name": openapi.Schema(type=openapi.TYPE_STRING),
                "raw_text": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            202: openapi.Response("Accepted — processing queued"),
            400: BAD_REQUEST,
            401: UNAUTHORIZED,
            503: openapi.Response("Celery queue unavailable"),
        },
        tags=["Ingestion"],
    )
    def post(self, request):
        serializer = UploadRecordCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
 
        data = serializer.validated_data
        file_type = data["file_type"]
 
        record_kwargs = {
            "user": request.user,
            "organization": getattr(request.user, "organization", None),   # <-- add this line
            "file_type": file_type,
            "file_name": data.get("file_name", "") or "",
            "status": UploadRecord.Status.PENDING,
        }   
 
        if file_type == "raw_text":
            record_kwargs.update(
                {
                    "file_url": "",
                    "file_name": data.get("file_name", "") or "Direct text input",
                    "raw_text": data["raw_text"],
                }
            )
        else:
            record_kwargs["file_url"] = data["file_url"]
 
        record = UploadRecord.objects.create(**record_kwargs)
 
        try:
            process_upload_async.delay(record.id)
        except Exception as exc:
            logger.error(f"Unable to queue UploadRecord {record.id} for processing: {exc}")
            record.status = UploadRecord.Status.FAILED
            record.error_message = str(exc)
            record.save(update_fields=["status", "error_message"])
            return Response(
                {
                    "error": "Upload processing could not be queued.",
                    "detail": str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
 
        return Response(
            UploadRecordResponseSerializer(record).data,
            status=status.HTTP_202_ACCEPTED,
        )
 
 
class UploadStatusView(APIView):
    """
    GET /api/ingestion/upload/<record_id>/
 
    Frontend polls this endpoint to check processing progress.
    Useful when you switch to async processing with Celery.
    """
 
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]
 
    @swagger_auto_schema(
        operation_summary="Poll upload / pipeline status",
        manual_parameters=[
            openapi.Parameter(
                "record_id",
                openapi.IN_PATH,
                type=openapi.TYPE_INTEGER,
                required=True,
            ),
        ],
        responses={
            200: openapi.Response("Upload record with status"),
            401: UNAUTHORIZED,
            404: NOT_FOUND,
        },
        tags=["Ingestion"],
    )
    def get(self, request, record_id):
        try:
            # Users can only see their own records
            record = UploadRecord.objects.get(id=record_id, user=request.user)
        except UploadRecord.DoesNotExist:
            return Response(
                {"error": "Record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
 
        return Response(UploadRecordResponseSerializer(record).data)
 
 
# Internal helper: trigger NLP + save coding results to DB
 
def _run_nlp_and_save(record, user):
    from nlp_engine.services import analyze_raw_text, NLPProcessingError
    from coding.models import CodingResult
    from coding.validation import validator
 
    try:
        result = analyze_raw_text(record.extracted_text)
    except NLPProcessingError as e:
        raise RuntimeError(str(e))
 
    validated = validator.validate_and_filter(result)
    all_codes = validated.get("codes", [])
    icd_codes = [c for c in all_codes if c.get("system") == "ICD10"]
    cpt_codes = [c for c in all_codes if c.get("system") == "CPT"]
 
    # Extract evidence from pipeline result
    extracted_evidence = result.get("extracted_evidence", {})
    validation_metadata = result.get("validation_metadata", {})
 
    CodingResult.objects.create(
        upload_record        = record,
        user                 = user,
        organization         = record.organization, 
        soap_note            = validated.get("soap", {}),
        icd_codes            = icd_codes,
        cpt_codes            = cpt_codes,
        raw_llm_output       = str(validated),
        extracted_evidence   = extracted_evidence,
        validation_metadata  = validation_metadata,
    )
 
# ---------------------------------------------------------------------------
# Partner-facing endpoints -- authenticated via organization API key, not
# a browser session. These are additive: the two views above (FileUploadView,
# UploadStatusView) are completely untouched and keep working exactly as
# before for the web app.
# ---------------------------------------------------------------------------
 
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from organizations.authentication import OrganizationAPIKeyAuthentication
from organizations.permissions import HasAPIKeyScope
from organizations.models import APIKeyScope
from .cloudinary_utils import upload_file_to_cloudinary
 
 
def guess_file_type(filename):
    if not filename:
        return "pdf"
    ext = filename.split(".")[-1].lower()
    if ext in ["pdf"]:
        return "pdf"
    elif ext in ["jpg", "jpeg", "png", "gif", "webp", "tiff", "bmp"]:
        return "image"
    elif ext in ["mp3", "wav", "m4a", "flac", "ogg", "aac", "webm"]:
        return "audio"
    return "pdf"
 
 
class PartnerSubmitDocumentView(APIView):
    """
    POST /api/ingestion/partner/documents/
 
    For a partner's server (EHR / insurer), not a browser. Authenticate with:
        Authorization: Bearer vmc_live_...
 
    Body can be JSON (for raw text submissions) or multipart/form-data (for file uploads).
 
    JSON payload:
        {
            "raw_text": "...",
            "file_name": "optional label",
            "submitted_by_employee": "optional -- e.g. 'J. Ahmed, RN'",
            "review_mode_override": "optional -- 'direct' or 'assisted'"
        }
 
    Multipart/Form-Data:
        file: Binary file (PDF, image, or audio)
        file_type: "pdf" | "image" | "audio" (optional, will guess from filename extension if omitted)
        file_name: "optional label"
        submitted_by_employee: "optional -- e.g. 'J. Ahmed, RN'"
        review_mode_override: "optional -- 'direct' or 'assisted'"
 
    The document is tagged with the calling organization automatically --
    the partner never specifies it themselves, so one organization's key
    can never submit on behalf of another.
    """
 
    authentication_classes = [OrganizationAPIKeyAuthentication]
    permission_classes = [HasAPIKeyScope]
    required_scope = APIKeyScope.SUBMIT
    parser_classes = [JSONParser, MultiPartParser, FormParser]
 
    @swagger_auto_schema(
        operation_summary="Partner API: submit a clinical document",
        manual_parameters=[
            openapi.Parameter(
                name="file",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description="The clinical document file to upload (PDF, image, or audio)."
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "raw_text": openapi.Schema(type=openapi.TYPE_STRING, description="Required only if submitting raw text directly without a file."),
                "file_type": openapi.Schema(type=openapi.TYPE_STRING, enum=["pdf", "image", "audio", "raw_text"], description="Type of the submission. If uploading a file, this defaults to guessing from the extension if not specified."),
                "file_name": openapi.Schema(type=openapi.TYPE_STRING),
                "submitted_by_employee": openapi.Schema(type=openapi.TYPE_STRING),
                "review_mode_override": openapi.Schema(type=openapi.TYPE_STRING, enum=["direct", "assisted"]),
            },
        ),
        responses={201: openapi.Response("Upload record created"), 400: BAD_REQUEST, 401: UNAUTHORIZED},
        tags=["Partner API"],
    )
    def post(self, request):
        api_key = request.auth
 
        if "file" in request.FILES:
            uploaded_file = request.FILES["file"]
 
            # Reject oversized files before spending time/bandwidth uploading
            # them to Cloudinary -- the extractor enforces this same 50MB cap
            # when it later downloads the file, so failing fast here just
            # avoids the wasted round trip.
            MAX_FILE_SIZE_MB = 50
            if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                return Response(
                    {"error": f"File exceeds the {MAX_FILE_SIZE_MB}MB limit."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
 
            # Determine file type
            file_type = request.data.get("file_type")
            if not file_type or file_type == "raw_text":
                file_type = guess_file_type(uploaded_file.name)
                
            # Upload file to Cloudinary
            try:
                file_url = upload_file_to_cloudinary(uploaded_file)
            except Exception as exc:
                logger.error(f"Cloudinary upload failed: {exc}")
                return Response(
                    {"error": f"Failed to upload file to cloud storage: {str(exc)}"},
                    status=status.HTTP_502_BAD_GATEWAY
                )
            
            serializer_data = {
                "file_url": file_url,
                "file_type": file_type,
                "file_name": request.data.get("file_name") or uploaded_file.name,
                "raw_text": ""
            }
        else:
            serializer_data = {
                "file_url": "",
                "file_type": "raw_text",
                "file_name": request.data.get("file_name") or "Partner API submission",
                "raw_text": request.data.get("raw_text", "")
            }
 
        serializer = UploadRecordCreateSerializer(data=serializer_data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
        data = serializer.validated_data
        record = UploadRecord.objects.create(
            user=None,
            organization=api_key.organization,
            submitted_by_employee=request.data.get("submitted_by_employee", ""),
            review_mode_override=request.data.get("review_mode_override", ""),
            file_type=data["file_type"],
            file_name=data.get("file_name", ""),
            file_url=data.get("file_url", ""),
            raw_text=data.get("raw_text", ""),
            status=UploadRecord.Status.PENDING,
        )
 
        try:
            process_upload_async.delay(record.id)
        except Exception as exc:
            logger.error(f"Unable to queue partner UploadRecord {record.id} for processing: {exc}")
            record.status = UploadRecord.Status.FAILED
            record.error_message = "Could not queue for processing."
            record.save(update_fields=["status", "error_message"])
 
        return Response(UploadRecordResponseSerializer(record).data, status=status.HTTP_201_CREATED)
 
 
 
class PartnerDocumentStatusView(APIView):
    """
    GET /api/ingestion/partner/documents/<id>/
 
    Poll for status, scoped to the calling organization only -- one
    partner's key can never see another partner's (or your own internal
    Internal org's) documents.
    """
 
    authentication_classes = [OrganizationAPIKeyAuthentication]
    permission_classes = [HasAPIKeyScope]
    required_scope = APIKeyScope.READ
    @swagger_auto_schema(
        operation_summary="Partner API: poll document status",
        operation_description=(
            "Returns upload/processing status. Once status is 'completed', the response "
            "also includes a nested 'coding_result' object with the generated ICD-10/CPT "
            "codes -- no separate call to /api/coding/ is needed."
        ),
        manual_parameters=[
            openapi.Parameter("record_id", openapi.IN_PATH, type=openapi.TYPE_INTEGER, required=True),
        ],
        responses={200: openapi.Response("Upload record with status and, once completed, nested codes"), 401: UNAUTHORIZED, 404: NOT_FOUND},
        tags=["Partner API"],
    )
    def get(self, request, record_id):
        api_key = request.auth
        try:
            record = UploadRecord.objects.get(id=record_id, organization=api_key.organization)
        except UploadRecord.DoesNotExist:
            return Response({"error": "Record not found."}, status=status.HTTP_404_NOT_FOUND)
 
        data = UploadRecordResponseSerializer(record).data
 
        # Nest the generated codes directly here once they exist, so the
        # partner doesn't need a second call to /api/coding/ just to see
        # what was produced. coding_result is the OneToOneField reverse
        # accessor set up in coding/models.py.
        from coding.serializers import CodingResultSerializer
        coding_result = getattr(record, "coding_result", None)
        data["coding_result"] = CodingResultSerializer(coding_result).data if coding_result else None
 
        return Response(data)