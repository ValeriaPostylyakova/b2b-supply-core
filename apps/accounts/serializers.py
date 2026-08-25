from typing import Any, TypedDict, cast
from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator
from django.db.models import QuerySet
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import Organization

User = get_user_model()


class UserCreatePayload(TypedDict):
    email: str
    password: str
    role: str
    organization: Organization | None


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


class OrganizationMeSerializer(serializers.ModelSerializer):
    id: serializers.UUIDField = serializers.UUIDField(
        source="external_id", read_only=True
    )

    class Meta:
        model = Organization
        fields = ["id", "name", "type"]


class UserDetailSerializer(UserSerializer):
    organization: OrganizationMeSerializer = OrganizationMeSerializer(read_only=True)

    class Meta:
        model = User
        fields = list(UserSerializer.Meta.fields) + ["organization"]


class UsersViewSetSerializer(UserSerializer):
    class Meta:
        model = User
        fields = list(UserSerializer.Meta.fields) + ["is_active"]


class UsersViewSetCreateSerializer(serializers.ModelSerializer):
    user_queryset: QuerySet[Any] = User.objects.all()

    email: serializers.EmailField = serializers.EmailField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=user_queryset,
                message="Пользователь с таким email уже существует.",
            )
        ],
    )
    role: serializers.CharField = serializers.CharField(required=True)
    password: serializers.CharField = serializers.CharField(
        required=True,
        write_only=True,
        validators=[
            MinLengthValidator(
                8, message="Пароль должен содержать не менее 8 символов."
            )
        ],
    )
    organization: serializers.SlugRelatedField = serializers.SlugRelatedField(
        slug_field="name",
        read_only=True
    )

    class Meta:
        model = User
        fields = ["email", "password", "role", "organization"]

    def validate_role(self, value: str) -> str:
        if value not in User.Roles.values:
            raise serializers.ValidationError("Такой роли не существует.")

        request: Request | None = self.context.get("request")
        if not request or not request.user:
            raise serializers.ValidationError("Ошибка контекста запроса")

        current_user_role: str = getattr(request.user, "role", "")

        is_supplier_invalid = (
            current_user_role == "SUPPLIER_ADMIN" and not value.startswith("SUPPLIER_")
        )
        is_buyer_invalid = current_user_role == "BUYER_ADMIN" and not value.startswith(
            "BUYER_"
        )

        if is_supplier_invalid or is_buyer_invalid:
            raise serializers.ValidationError(
                "У вас нет прав для создания пользователя с такой ролью."
            )

        return value

    def create(self, validated_data: dict[str, Any]) -> User:
        data = cast(UserCreatePayload, validated_data)

        password: str = data.pop('password')
        user = User.objects.create(**data)
        user.set_password(password)
        user.save()
        return user
