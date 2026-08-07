#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="${HOME}/smartcloset_backups"
RETENTION_COUNT=7
TS="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

cd "$REPO_ROOT/deploy"
docker compose stop backend

cd "$REPO_ROOT"
# backend/data はコンテナ(root実行)が作成するためroot所有。sqlite3の.backupは
# ソースディレクトリへの書き込み権限が必要なためsudoで実行する
sudo sqlite3 "backend/data/smartcloset.db" ".backup '${BACKUP_DIR}/smartcloset_backup_${TS}.db'"
sudo chown "$(id -u):$(id -g)" "${BACKUP_DIR}/smartcloset_backup_${TS}.db"
tar czf "${BACKUP_DIR}/smartcloset_backup_${TS}.tar.gz" --exclude=storage/tmp -C backend storage

cd "$REPO_ROOT/deploy"
docker compose start backend

# 世代整理: BACKUP_RETENTION_COUNT を超える古いバックアップを削除
mapfile -t TIMESTAMPS < <(find "$BACKUP_DIR" -maxdepth 1 -name 'smartcloset_backup_*.db' -printf '%f\n' \
  | sed -E 's/smartcloset_backup_(.*)\.db/\1/' | sort -r)
if [ "${#TIMESTAMPS[@]}" -gt "$RETENTION_COUNT" ]; then
  for old_ts in "${TIMESTAMPS[@]:$RETENTION_COUNT}"; do
    rm -f "${BACKUP_DIR}/smartcloset_backup_${old_ts}.db" "${BACKUP_DIR}/smartcloset_backup_${old_ts}.tar.gz"
  done
fi

echo "backup complete: ${BACKUP_DIR}/smartcloset_backup_${TS}.{db,tar.gz}"
