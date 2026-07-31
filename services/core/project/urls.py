from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from .health import healthz


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/healthz/", healthz, name="healthz"),
    path("api/v1/", include("identity.urls")),
    path("api/v1/", include("modules.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
