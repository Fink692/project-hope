import json
import os
import urllib.error
import urllib.request

from django.conf import settings
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


def ai_gateway_status():
    base_url = os.environ.get("AI_GATEWAY_URL", "").strip().rstrip("/")
    if not base_url:
        return {"status": "disabled", "runtime": "not configured"}
    headers = {"Accept": "application/json"}
    token = os.environ.get("AI_GATEWAY_TOKEN", "")
    if token:
        headers["X-Project-Hope-Gateway-Token"] = token
    request = urllib.request.Request(
        f"{base_url}/healthz", headers=headers, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else {"status": "unknown"}
    except (TimeoutError, ValueError, urllib.error.URLError, urllib.error.HTTPError):
        return {"status": "unavailable", "runtime": "gateway unreachable"}


@api_view(["GET"])
@permission_classes([AllowAny])
def healthz(request):
    database_status = "ok"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        database_status = "unavailable"

    status = "ok" if database_status == "ok" else "degraded"
    return Response(
        {
            "status": status,
            "database": database_status,
            "service": "project-hope-core",
            "ai": ai_gateway_status(),
            "mode": "showcase"
            if getattr(settings, "PROJECT_HOPE_DESKTOP_SHOWCASE", False)
            else "connected",
        },
        status=200 if status == "ok" else 503,
    )
