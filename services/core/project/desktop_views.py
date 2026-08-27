"""Routes enabled only in the token-protected bundled showcase runtime."""

from django.contrib.auth import login
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from identity.mfa import SESSION_SECURITY_VERSION_KEY
from identity.models import User


@never_cache
@require_GET
def start_showcase(request):
    # The outer DesktopGuard requires the per-launch secret on every request.
    # This route does not exist in hosted/development settings.
    user = User.objects.get(email="showcase@example.org", is_active=True)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session[SESSION_SECURITY_VERSION_KEY] = user.security_version
    return HttpResponseRedirect("/#workspace")


@never_cache
@require_GET
def desktop_status(request):
    return JsonResponse(
        {
            "mode": "showcase",
            "syntheticData": True,
            "externalSendingEnabled": False,
            "message": "A private sample workspace on this computer. Use sample data only.",
        }
    )
