from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import CookieTokenObtainView, CookieTokenRefreshView, MeView, UsersViewSet

router = DefaultRouter()

router.register('auth/users', UsersViewSet, basename='users')

urlpatterns = [
    path('auth/token/', CookieTokenObtainView.as_view(), name='token_obtain'),
    path('auth/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', MeView.as_view(), name='me')

]

urlpatterns += router.urls
