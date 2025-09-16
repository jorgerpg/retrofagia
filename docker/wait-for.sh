#!/usr/bin/env bash
set -e
host="$1"; shift
until pg_isready -h "$host"; do
  >&2 echo "Aguardando Postgres em $host..."
  sleep 2
done
exec "$@"