from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator
from mypy.dmypy.client import request
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import Organization

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    id: serializers.UUIDField = serializers.UUIDField(source='external_id', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'role']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = UserSerializer(self.user)
        data['user'] = user.data

        return data

class OrganizationMeSerializer(serializers.ModelSerializer):
    id: serializers.UUIDField = serializers.UUIDField(source='external_id', read_only=True)

    class Meta:
        model = Organization
        fields = ['id', 'name', 'type']

class UserDetailSerializer(UserSerializer):
    organization = OrganizationMeSerializer(read_only=True)

    class Meta:
        model = User
        fields = list(UserSerializer.Meta.fields) + ['organization']

class UsersViewSetSerializer(UserSerializer):
    class Meta:
        model = User
        fields = list(UserSerializer.Meta.fields) + ['is_active']


class UsersViewSetCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True, validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="Пользователь с таким email уже существует."
            )
        ])
    role = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[MinLengthValidator(8, message='Пароль должен содержать не менее 8 символов.')]
    )
    organization = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = User
        fields = ['email', 'password',  'role', 'organization',]

    def validate(self, data):
        request = self.context['request']

        if not request or not request.user:
            raise serializers.ValidationError("Ошибка контекста запроса")

        current_user_organization = getattr(request.user, 'organization', None)
        data['organization'] = current_user_organization
        return data

    def validate_role(self, value):
        if value not in User.Roles.values:
            raise serializers.ValidationError("Такой роли не существует.")

        current_user_role = self.context['request'].user.role

        if (current_user_role == 'SUPPLIER_ADMIN' and not value.startswith('SUPPLIER_')) | (current_user_role == 'BUYER_ADMIN' and not value.startswith('BUYER_')):
            raise serializers.ValidationError("У вас нет прав для создания пользователя с такой ролью.")

        return value



    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user




