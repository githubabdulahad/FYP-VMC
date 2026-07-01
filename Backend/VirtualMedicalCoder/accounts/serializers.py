from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

User = get_user_model()

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        write_only = True,
        style = {"input_type": "password"},
    )

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        user = authenticate(
            request = self.context.get("request"),
            username = username,
            password = password
        )

        if not user:
            raise serializers.ValidationError(
                "Invalid username or password. Please try again."
            )
 
        if not user.is_active:
            raise serializers.ValidationError("This account has been disabled.")
 
        # Attach the user object so the view can access it via serializer.validated_data
        data["user"] = user
        return data


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "confirm_password"]

    def validate_username(self, value):
        username = value.strip()
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return username

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate(self, attrs):
        password = attrs.get("password")
        confirm_password = attrs.pop("confirm_password", None)

        if password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        try:
            validate_password(password)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            role="coder",
        )
        return user
    
class UserSerializer(serializers.Serializer):
    """
    Represents the logged-in user in the login response body.
    Never expose sensitive fields like password here.
    """
 
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    is_staff = serializers.BooleanField()
    role = serializers.CharField()


class ProfileUpdateSerializer(serializers.Serializer):
    """
    Validates a PATCH /api/auth/me/ request.
    All fields are optional — only provided fields are updated.
    """

    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name  = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email      = serializers.EmailField(required=False)

    # Password change — both required together if either is supplied
    current_password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})
    new_password     = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})
    confirm_new_password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})

    def validate_email(self, value):
        email = value.strip().lower()
        user = self.context["request"].user
        if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate(self, attrs):
        current  = attrs.get("current_password")
        new_pw   = attrs.get("new_password")
        confirm  = attrs.get("confirm_new_password")

        # If any password field is supplied, all three must be present
        if any([current, new_pw, confirm]):
            if not all([current, new_pw, confirm]):
                raise serializers.ValidationError(
                    "Provide current_password, new_password, and confirm_new_password together."
                )
            # Verify current password
            user = self.context["request"].user
            if not user.check_password(current):
                raise serializers.ValidationError({"current_password": "Current password is incorrect."})
            # New passwords must match
            if new_pw != confirm:
                raise serializers.ValidationError({"confirm_new_password": "New passwords do not match."})
            # Validate strength
            try:
                validate_password(new_pw, user=user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"new_password": list(exc.messages)})

        return attrs