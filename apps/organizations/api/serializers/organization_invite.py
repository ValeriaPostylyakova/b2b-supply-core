from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.organizations.models.organization_invite import OrganizationInvite

User = get_user_model()


class OrganizationInviteSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id")

    class Meta:
        model = OrganizationInvite
        fields = ["id", "email", "role", "status", "accepted_at", "expires_at"]


class OrganizationInviteCreateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(choices=User.Roles.choices, required=True)
