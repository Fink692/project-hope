import email
import imaplib
import os
from email.header import decode_header
from email.policy import default

from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.models import EmailMessage, Mailbox


INJECTION_MARKERS = {
    "ignore previous",
    "system prompt",
    "reveal password",
    "execute command",
    "grant access",
}


def decoded_header(value):
    parts = []
    for chunk, encoding in decode_header(value or ""):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(encoding or "utf-8", errors="replace"))
        else:
            parts.append(chunk)
    return "".join(parts)


def message_excerpt(message):
    body = message.get_body(preferencelist=("plain", "html"))
    if body is None:
        return ""
    text = body.get_content()
    return text[:12000]


def import_mailbox(mailbox, limit=25):
    password_env = mailbox.credential_ref or ""
    password = os.environ.get(password_env, "") if password_env else ""
    if not mailbox.host or not mailbox.username or not password:
        return {
            "mailbox": mailbox.name,
            "status": "skipped",
            "reason": "host, username, or credential is not configured",
        }
    imported = 0
    connection = imaplib.IMAP4_SSL(mailbox.host, mailbox.port)
    try:
        connection.login(mailbox.username, password)
        connection.select("INBOX", readonly=True)
        result, data = connection.search(None, "UNSEEN")
        if result != "OK":
            return {
                "mailbox": mailbox.name,
                "status": "failed",
                "reason": "mailbox search failed",
            }
        message_ids = data[0].split()[-limit:]
        for message_id in message_ids:
            result, fetched = connection.fetch(message_id, "(RFC822)")
            if result != "OK":
                continue
            raw = next((item[1] for item in fetched if isinstance(item, tuple)), b"")
            parsed = email.message_from_bytes(raw, policy=default)
            external_id = parsed.get("Message-ID") or message_id.decode(
                "ascii", errors="replace"
            )
            excerpt = message_excerpt(parsed)
            flags = sorted(
                marker for marker in INJECTION_MARKERS if marker in excerpt.lower()
            )
            EmailMessage.objects.update_or_create(
                organization=mailbox.organization,
                mailbox=mailbox,
                external_id=external_id[:240],
                defaults={
                    "sender": email.utils.parseaddr(
                        parsed.get("From", "unknown@example.org")
                    )[1]
                    or "unknown@example.org",
                    "recipients": [
                        address
                        for _, address in email.utils.getaddresses(
                            parsed.get_all("To", [])
                        )
                    ],
                    "subject": decoded_header(parsed.get("Subject", ""))[:500],
                    "body_excerpt": excerpt,
                    "received_at": timezone.now(),
                    "injection_flags": flags,
                },
            )
            imported += 1
        mailbox.last_polled_at = timezone.now()
        mailbox.save(update_fields=["last_polled_at", "updated_at"])
        return {"mailbox": mailbox.name, "status": "ok", "imported": imported}
    finally:
        try:
            connection.logout()
        except imaplib.IMAP4.error:
            pass


class Command(BaseCommand):
    help = "Poll active mailbox integrations and store minimized, injection-flagged message records."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25)

    def handle(self, *args, **options):
        for mailbox in Mailbox.objects.filter(active=True):
            try:
                result = import_mailbox(
                    mailbox, limit=max(1, min(options["limit"], 100))
                )
            except (OSError, imaplib.IMAP4.error) as exc:
                result = {
                    "mailbox": mailbox.name,
                    "status": "failed",
                    "reason": type(exc).__name__,
                }
            self.stdout.write(str(result))
