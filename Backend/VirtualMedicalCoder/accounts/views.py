import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
# pyrefly: ignore [missing-import]
from drf_yasg import openapi
# pyrefly: ignore [missing-import]
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from VirtualMedicalCoder.swagger import AUTH_COOKIE_DESC, BAD_REQUEST, UNAUTHORIZED
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer, ProfileUpdateSerializer
# pyrefly: ignore [missing-import]
from .authentication import JWTCookieAuthentication
# pyrefly: ignore [missing-import]
from .tokens import (
    delete_auth_cookies,
    generate_access_token,
    generate_refresh_token,
    set_auth_cookies,
)
 
User = get_user_model()

class RegisterView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Register a new coder account",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "email", "password", "confirm_password"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                "confirm_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
            },
        ),
        responses={
            201: openapi.Response("User created"),
            400: BAD_REQUEST,
        },
        tags=["Authentication"],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": "User registered successfully",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "role": user.role,
                    },
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Log in (sets HttpOnly JWT cookies)",
        operation_description=AUTH_COOKIE_DESC,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["username", "password"],
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
            },
        ),
        responses={200: openapi.Response("Login successful — cookies set"), 400: BAD_REQUEST},
        tags=["Authentication"],
    )
    def post(self , request):
        serializer = LoginSerializer(
            data = request.data , 
            context = {"request": request},
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.validated_data["user"]
 
        # Generate both tokens
        access_token = generate_access_token(user=user)
        refresh_token = generate_refresh_token(user=user)

        # Build response — return user info in body, tokens go in cookies
        response = Response(
            {
                "message": "Login successful.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
 
        # Attach tokens as HttpOnly cookies
        set_auth_cookies(response, access_token, refresh_token)
 
        return response

class LogoutView(APIView):
    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Log out (clears auth cookies)",
        responses={200: openapi.Response("Logged out"), 401: UNAUTHORIZED},
        tags=["Authentication"],
    )
    def post(self , request):
        response = Response(
            {"message": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )
        delete_auth_cookies(response)
        return response

class TokenRefreshView(APIView):
    """
    POST /api/auth/refresh/
 
    Reads the refresh_token cookie, verifies it, and issues a new
    access token. The refresh cookie is restricted to this path only.
    """
 
    authentication_classes = []
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Refresh access token using refresh cookie",
        operation_description="Requires `refresh_token` HttpOnly cookie from login.",
        responses={200: openapi.Response("New access token cookie set"), 401: UNAUTHORIZED},
        tags=["Authentication"],
    )
    def post(self, request):
        config = settings.JWT_AUTH
        refresh_token = request.COOKIES.get(config["AUTH_COOKIE_REFRESH"])
 
        if not refresh_token:
            return Response(
                {"error": "Refresh token not found. Please log in again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
 
        # Decode and validate the refresh token
        try:
            payload = jwt.decode(
                refresh_token,
                config["SIGNING_KEY"],
                algorithms=[config["ALGORITHM"]],
            )
        except jwt.ExpiredSignatureError:
            return Response(
                {"error": "Refresh token expired. Please log in again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except jwt.InvalidTokenError:
            return Response(
                {"error": "Invalid refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
 
        # Reject if someone tries to use an access token as a refresh token
        if payload.get("type") != "refresh":
            return Response(
                {"error": "Invalid token type."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
 
        # Look up the user
        try:
            user = User.objects.get(id=payload["user_id"])
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
 
        if not user.is_active:
            return Response(
                {"error": "User account is disabled."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
 
        # Issue a fresh access token
        new_access_token = generate_access_token(user)
 
        response = Response(
            {"message": "Token refreshed successfully."},
            status=status.HTTP_200_OK,
        )
 
        # Only update the access token cookie — keep the same refresh token
        set_auth_cookies(response, new_access_token, refresh_token=None)
 
        return response
 
 
class MeView(APIView):
    """
    GET  /api/auth/me/  — Return the logged-in user's profile.
    PATCH /api/auth/me/ — Update profile fields (name, email, password).

    JWTCookieAuthentication reads the access_token cookie and populates
    request.user.  All fields in PATCH are optional — send only what changed.
    """

    authentication_classes = [JWTCookieAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get current authenticated user's profile",
        operation_description="Returns the logged-in user's id, username, email, name, role, and staff status.",
        responses={200: openapi.Response("User profile"), 401: UNAUTHORIZED},
        tags=["Profile"],
    )
    def get(self, request):
        return Response(
            {"user": UserSerializer(request.user).data},
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary="Update current user's profile",
        operation_description=(
            "Partially update first_name, last_name, and/or email.\n\n"
            "To change password, supply `current_password`, `new_password`, "
            "and `confirm_new_password` together."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "first_name":          openapi.Schema(type=openapi.TYPE_STRING),
                "last_name":           openapi.Schema(type=openapi.TYPE_STRING),
                "email":               openapi.Schema(type=openapi.TYPE_STRING, format="email"),
                "current_password":    openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                "new_password":        openapi.Schema(type=openapi.TYPE_STRING, format="password"),
                "confirm_new_password": openapi.Schema(type=openapi.TYPE_STRING, format="password"),
            },
        ),
        responses={
            200: openapi.Response("Updated user profile"),
            400: BAD_REQUEST,
            401: UNAUTHORIZED,
        },
        tags=["Profile"],
    )
    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user = request.user

        # Apply simple field updates
        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "email" in data:
            user.email = data["email"]

        # Apply password change if requested
        if data.get("new_password"):
            user.set_password(data["new_password"])

        user.save()

        return Response(
            {
                "message": "Profile updated successfully.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
 