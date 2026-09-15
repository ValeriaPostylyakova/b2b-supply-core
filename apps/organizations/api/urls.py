from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.organizations.api.views.organization import MyCompanyAPIView
from apps.organizations.api.views.organization_invite import MyCompanyInviteViewSet

router = DefaultRouter()

router.register("my-company/invites/", MyCompanyInviteViewSet, basename="invites")

urlpatterns = [
    path("my-company/", view=MyCompanyAPIView.as_view(), name="my-company"),
]
