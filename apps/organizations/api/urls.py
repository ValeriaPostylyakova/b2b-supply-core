from django.urls import path

from apps.organizations.api.views.organization import MyCompanyAPIView

urlpatterns = [
    path("my-company/", view=MyCompanyAPIView.as_view(), name="my-company"),
]
