"""Bundled desktop entry point. Listens on a private, authenticated loopback port."""

import argparse
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import sys
import threading
import time


def configure_environment(data_dir):
    token = os.environ.get("PROJECT_HOPE_DESKTOP_TOKEN", "")
    if len(token) < 40:
        raise ValueError("Launch Project Hope from the desktop app.")
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    secret_path = data_dir / "workspace.secret"
    try:
        with secret_path.open("x", encoding="utf-8") as secret_file:
            secret_file.write(secrets.token_urlsafe(64))
        secret_path.chmod(0o600)
    except FileExistsError:
        pass
    secret = secret_path.read_text(encoding="utf-8").strip()
    if len(secret) < 40:
        raise ValueError("The sample workspace key is damaged. Contact support.")
    os.environ.update(
        {
            "DJANGO_SETTINGS_MODULE": "project.desktop_settings",
            "DJANGO_ENV": "desktop",
            "DJANGO_DEBUG": "false",
            "DJANGO_SECRET_KEY": secret,
            "DATABASE_URL": "",
            "VALKEY_URL": "",
            "PROJECT_HOPE_DESKTOP_DATA_DIR": str(data_dir),
            "PROJECT_HOPE_MFA_REQUIRED": "false",
            "PROJECT_HOPE_MFA_ENCRYPTION_KEYS": "",
            "DJANGO_TRUST_PROXY": "false",
            "DJANGO_SECURE_SSL_REDIRECT": "false",
            "AI_GATEWAY_TOKEN": secrets.token_urlsafe(48),
            "AI_GATEWAY_TIMEOUT_SECONDS": "55",
            "AI_GATEWAY_ENV": "desktop",
            "AI_PROVIDER": "ollama",
            "AI_OLLAMA_URL": "http://127.0.0.1:11434",
        }
    )
    return token


def start_gateway():
    import uvicorn

    source = (
        Path(getattr(sys, "_MEIPASS", "")) / "main.py"
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent.parent / "ai-gateway" / "main.py"
    )
    spec = importlib.util.spec_from_file_location("hope_ai_gateway", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("The bundled AI adapter is missing.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    gateway_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    gateway_socket.bind(("127.0.0.1", 0))
    gateway_socket.listen(128)
    port = gateway_socket.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            module.app, log_level="warning", access_log=False, lifespan="off"
        )
    )
    threading.Thread(
        target=server.run, kwargs={"sockets": [gateway_socket]}, daemon=True
    ).start()
    os.environ["AI_GATEWAY_URL"] = f"http://127.0.0.1:{port}"
    return server


def main():
    parser = argparse.ArgumentParser(description="Project Hope desktop workspace")
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--web-root", required=True, type=Path)
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    web_root = args.web_root.resolve()
    if not (web_root / "index.html").is_file():
        raise ValueError(
            "The application files are incomplete. Reinstall Project Hope."
        )
    token = configure_environment(data_dir)
    import django

    django.setup()
    from django.core.management import call_command
    from django.core.wsgi import get_wsgi_application
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from waitress import create_server
    from whitenoise import WhiteNoise

    from project.desktop_guard import DesktopGuard

    executor = MigrationExecutor(connection)
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        database = data_dir / "showcase.sqlite3"
        if database.exists() and database.stat().st_size:
            backups = data_dir / "backups"
            backups.mkdir(exist_ok=True)
            with sqlite3.connect(database) as source:
                with sqlite3.connect(
                    backups / f"before-update-{time.time_ns()}.sqlite3"
                ) as backup:
                    source.backup(backup)
        with contextlib.redirect_stdout(sys.stderr):
            call_command("migrate", interactive=False, verbosity=0)
    with contextlib.redirect_stdout(sys.stderr):
        call_command("seed_showcase", verbosity=0)

    gateway = start_gateway()
    application = WhiteNoise(
        get_wsgi_application(), root=str(web_root), index_file=True, max_age=0
    )
    # Waitress owns the socket from binding through serving, avoiding port races.
    server = create_server(
        application,
        host="127.0.0.1",
        port=0,
        threads=4,
        max_request_body_size=30 * 1024 * 1024,
        ident="Project Hope",
        clear_untrusted_proxy_headers=True,
    )
    origin = f"http://127.0.0.1:{server.effective_port}"
    server.application = DesktopGuard(application, token=token, origin=origin)

    def watch_parent():
        # Closing the parent's pipe or asking for shutdown closes the runtime.
        sys.stdin.readline()
        gateway.should_exit = True
        server.close()
        os._exit(0)

    threading.Thread(target=watch_parent, daemon=True).start()
    print(json.dumps({"event": "ready", "url": origin, "mode": "showcase"}), flush=True)
    server.run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Keep details in the local diagnostic log, never in the first-run UI.
        import traceback

        traceback.print_exc(file=sys.stderr)
        print(
            json.dumps(
                {"event": "error", "message": "The sample workspace could not start."}
            ),
            flush=True,
        )
        sys.exit(1)
