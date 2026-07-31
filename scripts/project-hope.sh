#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deploy/podman/compose.yml"
ENGINE=""

show_help() {
  cat <<'EOF'

Project Hope - simple local workspace

Use these commands from the project folder:

  bash scripts/project-hope.sh setup   First-time setup and start services
  bash scripts/project-hope.sh start   Start the workspace
  bash scripts/project-hope.sh stop    Stop the workspace without deleting data
  bash scripts/project-hope.sh status  Show service status
  bash scripts/project-hope.sh logs    Show recent service logs
  bash scripts/project-hope.sh doctor  Check the computer before setup

Plain-language guide: docs/GETTING_STARTED_FOR_CHARITIES.md

EOF
}

find_engine() {
  if [[ -n "${PROJECT_HOPE_CONTAINER_ENGINE:-}" ]]; then
    ENGINE="$PROJECT_HOPE_CONTAINER_ENGINE"
  elif command -v docker >/dev/null 2>&1; then
    ENGINE="docker"
  elif command -v podman >/dev/null 2>&1; then
    ENGINE="podman"
  else
    echo "Project Hope needs Docker Desktop or Podman Desktop. Install one, start it, and run this command again." >&2
    echo "See docs/GETTING_STARTED_FOR_CHARITIES.md." >&2
    return 1
  fi
}

check_ready() {
  [[ -f "$COMPOSE_FILE" ]] || { echo "Project Hope's workspace file is missing: $COMPOSE_FILE" >&2; return 1; }
  find_engine
  if ! "$ENGINE" info >/dev/null 2>&1; then
    echo "$ENGINE is installed but not running. Open Docker Desktop or Podman Desktop, wait until it says it is ready, and try again." >&2
    return 1
  fi
}

compose() {
  "$ENGINE" compose -f "$COMPOSE_FILE" "$@"
}

wait_for_workspace() {
  local health_url="http://localhost:8090/api/v1/healthz/"
  command -v curl >/dev/null 2>&1 || return 0
  echo "Waiting for Project Hope to become ready..."
  for _ in {1..30}; do
    if curl --silent --show-error --fail --max-time 2 "$health_url" >/dev/null; then
      return 0
    fi
    sleep 2
  done
  echo "The services are still starting. Run 'bash scripts/project-hope.sh status' for details."
}

start_workspace() {
  check_ready
  echo "Starting Project Hope. The first start may take a few minutes while images are prepared."
  compose up -d --build
  wait_for_workspace
  echo "Project Hope is available at http://localhost:8090"
}

COMMAND="${1:-help}"
case "$COMMAND" in
  help)
    show_help
    ;;
  doctor)
    check_ready
    echo "Everything needed for the local workspace is ready."
    ;;
  setup)
    start_workspace
    if command -v open >/dev/null 2>&1; then open "http://localhost:8090";
    elif command -v xdg-open >/dev/null 2>&1; then xdg-open "http://localhost:8090" >/dev/null 2>&1 & fi
    cat <<'EOF'

Sign in for this local workspace:
  Email:    demo@example.org
  Password: change-me-now

This account is for local setup only. Change the identity setup before using real charity data.
EOF
    ;;
  start)
    start_workspace
    ;;
  stop)
    check_ready
    compose down
    echo "Project Hope is stopped. Your named data volumes were not deleted."
    ;;
  status)
    check_ready
    compose ps
    ;;
  logs)
    check_ready
    compose logs --tail 80
    ;;
  *)
    echo "Unknown command: $COMMAND" >&2
    show_help
    exit 2
    ;;
esac
