import hashlib

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.models import DocumentPassage, DocumentRecord


@transaction.atomic
def process_document(document):
    document.status = DocumentRecord.Status.PROCESSING
    document.save(update_fields=["status", "updated_at"])
    with document.file.open("rb") as handle:
        raw = handle.read(5 * 1024 * 1024)
    text = raw.decode("utf-8", errors="replace")
    document.extracted_text = text
    document.size_bytes = len(raw)
    document.checksum = hashlib.sha256(raw).hexdigest()
    document.status = DocumentRecord.Status.READY
    document.save(
        update_fields=[
            "extracted_text",
            "size_bytes",
            "checksum",
            "status",
            "updated_at",
        ]
    )
    DocumentPassage.objects.filter(document=document).delete()
    DocumentPassage.objects.create(
        organization=document.organization,
        document=document,
        text=text[:100000],
        source_locator="page:1",
    )


class Command(BaseCommand):
    help = (
        "Process uploaded text-readable documents using the local extraction fallback."
    )

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **options):
        documents = DocumentRecord.objects.filter(
            status=DocumentRecord.Status.UPLOADED
        )[: max(1, min(options["limit"], 100))]
        for document in documents:
            try:
                process_document(document)
                self.stdout.write(self.style.SUCCESS(f"processed {document.id}"))
            except (OSError, UnicodeError) as exc:
                document.status = DocumentRecord.Status.FAILED
                document.save(update_fields=["status", "updated_at"])
                self.stderr.write(f"failed {document.id}: {type(exc).__name__}")
