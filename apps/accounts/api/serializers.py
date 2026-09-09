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


class ProfileSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    organization = OrganizationShortSerializer(read_only=True)
    avatar = serializers.ImageField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "avatar",
            "role",
            "is_active",
            "organization",
        ]
