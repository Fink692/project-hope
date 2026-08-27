from django.urls import path

from .desktop_views import desktop_status, start_showcase
from .urls import urlpatterns as core_urlpatterns


urlpatterns = [
    path("desktop/start/", start_showcase, name="desktop-start"),
    path("api/v1/desktop/", desktop_status, name="desktop-status"),
    *core_urlpatterns,
]
