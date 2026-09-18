from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.organizations.models.organization_invite import OrganizationInvite

User = get_user_model()


class OrganizationInviteListSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id")

    class Meta:
        model = OrganizationInvite
        fields = ["id", "email", "role", "status", "accepted_at", "expires_at"]


class OrganizationInviteCreateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(choices=User.Roles.choices, required=True)


class OrganizationAcceptInviteSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)


class OrganizationInviteRegistrationSerializer(serializers.Serializer):
    registration_token = serializers.CharField(required=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    username = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким username уже существует."
            )
        return value
