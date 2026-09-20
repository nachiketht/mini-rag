#!/usr/bin/env bash
# Start the local Postgres cluster and apply the mini_rag schema.
# This VM has no Docker daemon and no systemd, so compose/service start
# cannot bring the database up after a reboot or stale pid file.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INIT_SQL="$ROOT/sql/001_init.sql"

if ! command -v pg_ctlcluster >/dev/null 2>&1; then
  echo "PostgreSQL is not installed (pg_ctlcluster not found)." >&2
  exit 1
fi

cluster_line="$(pg_lsclusters --no-header 2>/dev/null | awk 'NF {print; exit}')"
version="$(awk '{print $1}' <<<"$cluster_line")"
name="$(awk '{print $2}' <<<"$cluster_line")"
version="${version:-15}"
name="${name:-main}"

if ! pg_isready -q 2>/dev/null; then
  pg_ctlcluster "$version" "$name" start
fi

for _ in $(seq 1 50); do
  if pg_isready -q 2>/dev/null; then
    break
  fi
  sleep 0.2
done

if ! pg_isready -q 2>/dev/null; then
  echo "PostgreSQL did not become ready on port 5432." >&2
  exit 1
fi

run_as_postgres() {
  # postgres cannot cd into /root; run from a world-readable directory.
  (cd /tmp && su -s /bin/sh postgres -c "$1")
}

run_as_postgres "psql -v ON_ERROR_STOP=1 -d postgres -c \"ALTER USER postgres WITH PASSWORD 'postgres';\""
if ! run_as_postgres "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='mini_rag'\"" | grep -q 1; then
  run_as_postgres "createdb mini_rag"
fi
# Pipe SQL so the postgres user does not need filesystem access to the repo.
run_as_postgres "psql -v ON_ERROR_STOP=1 -d mini_rag" < "$INIT_SQL"
