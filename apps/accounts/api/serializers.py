from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.organizations.api.serializers import OrganizationShortSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    id: serializers.UUIDField = serializers.UUIDField(
        source="external_id", read_only=True
    )

    class Meta:
        model = User
        fields = ["id", "email", "role"]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = super().validate(attrs)
        user = UserSerializer(self.user)
        data["user"] = user.data

        return data


class MeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    organization = OrganizationShortSerializer(read_only=True)
    avatar = serializers.ImageField(required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "username",
            "avatar",
            "role",
            "is_active",
            "organization",
        ]

        read_only_fields = [
            "id",
            "role",
            "is_active",
            "organization",
            "username",
        ]

    def validate_avatar(self, value):
        MAX_FILE_SIZE = 5 * 1024 * 1024
        if value.size > MAX_FILE_SIZE:
            raise serializers.ValidationError("Размер файла не должен превышать 5 МБ.")

        ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
        ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"]

        import os

        ext = os.path.splitext(value.name)[1].lower()
        file_mime_type = getattr(value, "content_type", None)

        if ext not in ALLOWED_EXTENSIONS or file_mime_type not in ALLOWED_MIME_TYPES:
            raise serializers.ValidationError(
                "Недопустимый формат файла. Разрешены только JPG, JPEG, PNG и WEBP."
            )

        return value
