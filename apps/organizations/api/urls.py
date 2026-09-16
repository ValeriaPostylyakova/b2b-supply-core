from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.organizations.api.views.organization import MyCompanyAPIView
from apps.organizations.api.views.organization_invite import (
    InviteAcceptAPIView,
    InviteRegisterAPIView,
    OrganizationInviteViewSet,
)

router = DefaultRouter()

router.register("my-company/invites", OrganizationInviteViewSet, basename="invites")

urlpatterns = [
    path(
        "my-company/invites/accept/",
        InviteAcceptAPIView.as_view(),
        name="accept-invite",
    ),
    path(
        "my-company/invites/register/",
        InviteRegisterAPIView.as_view(),
        name="accept-invite",
    ),
    path("my-company/", view=MyCompanyAPIView.as_view(), name="my-company"),
]

urlpatterns += router.urls
