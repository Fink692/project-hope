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
        while True:
            management.call_command("poll_mailboxes", verbosity=0)
            management.call_command("process_documents", verbosity=0)
            if options["once"]:
                return
            time.sleep(interval)
