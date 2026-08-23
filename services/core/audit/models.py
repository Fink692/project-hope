import uuid
from ipaddress import ip_address

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def request_ip_address(request):
    remote_address = request.META.get("REMOTE_ADDR", "")
    forwarded = [
        value.strip()
        for value in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")
        if value.strip()
    ]
    proxy_count = int(settings.REST_FRAMEWORK.get("NUM_PROXIES", 0))
    candidate = (
        forwarded[-proxy_count]
        if proxy_count > 0 and len(forwarded) >= proxy_count
        else remote_address
    )
    try:
        return str(ip_address(candidate))
    except ValueError:
        return None


class AuditEventManager(models.Manager):
    def record(
        self,
        *,
        action: str,
        event_type: str = "security",
        organization=None,
        actor=None,
        resource_type: str = "",
        resource_id: str = "",
        metadata: dict | None = None,
        request=None,
    ):
        request_meta = {}
        if request is not None:
            request_meta = {
                "ip_address": request_ip_address(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:512],
            }
        return self.create(
            action=action,
            event_type=event_type,
            organization=organization,
            actor=actor,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else "",
            metadata=metadata or {},
            **request_meta,
        )


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    event_type = models.CharField(max_length=64)
    action = models.CharField(max_length=128)
    resource_type = models.CharField(max_length=128, blank=True)
    resource_id = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AuditEventManager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["actor", "-created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError("Audit events are append-only and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events are append-only and cannot be deleted.")
