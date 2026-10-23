from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("products.urls")),
    path("", lambda request: redirect("home_view", permanent=False)),
    path("api/token/", obtain_auth_token, name="api_token"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api_schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api_schema"), name="api_docs"),
]
