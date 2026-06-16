from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from VirtualMedicalCoder.swagger import BAD_REQUEST
from .serializers import AnalyzeInputRequestSerializer
from .services import NLPProcessingError, analyze_raw_text


class AnalyzeInputRecordView(APIView):
	permission_classes = [AllowAny]

	@swagger_auto_schema(
		operation_summary="Analyze raw clinical text (direct NLP, no persistence)",
		request_body=openapi.Schema(
			type=openapi.TYPE_OBJECT,
			required=["raw_text"],
			properties={
				"raw_text": openapi.Schema(type=openapi.TYPE_STRING),
				"model": openapi.Schema(type=openapi.TYPE_STRING, description="Optional LLM model override"),
			},
		),
		responses={
			200: openapi.Response("SOAP + codes analysis"),
			400: BAD_REQUEST,
			502: openapi.Response("NLP processing error"),
		},
		tags=["NLP"],
	)
	def post(self, request):
		request_serializer = AnalyzeInputRequestSerializer(data=request.data)
		if not request_serializer.is_valid():
			return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

		raw_text = request_serializer.validated_data["raw_text"]
		model_name = request_serializer.validated_data.get("model")

		try:
			analysis = analyze_raw_text(raw_text, model=model_name)
		except NLPProcessingError as exc:
			return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

		return Response(analysis, status=status.HTTP_200_OK)
