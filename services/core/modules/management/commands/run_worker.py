import os
import time

from django.core import management
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the local first background worker for mailbox polling and document processing."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        interval = max(5, int(os.environ.get("PROJECT_HOPE_WORKER_INTERVAL", "60")))
        cleanup_interval = max(
            3600,
            int(os.environ.get("PROJECT_HOPE_PILOT_CLEANUP_INTERVAL", "86400")),
        )
        next_pilot_cleanup = 0.0
        while True:
            management.call_command("poll_mailboxes", verbosity=0)
            management.call_command("process_documents", verbosity=0)
            management.call_command("retry_pilot_verification_emails", verbosity=0)
            now = time.monotonic()
            if now >= next_pilot_cleanup:
                management.call_command(
                    "purge_pilot_applications", execute=True, verbosity=0
                )
                next_pilot_cleanup = now + cleanup_interval
            if options["once"]:
                return
            time.sleep(interval)
