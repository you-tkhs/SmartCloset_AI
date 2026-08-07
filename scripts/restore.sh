#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $0 <timestamp: YYYYMMDD_HHMMSS>" >&2
  exit 1
fi

TS="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="${HOME}/smartcloset_backups"
DB_BACKUP="${BACKUP_DIR}/smartcloset_backup_${TS}.db"
STORAGE_BACKUP="${BACKUP_DIR}/smartcloset_backup_${TS}.tar.gz"

if [ ! -f "$DB_BACKUP" ] || [ ! -f "$STORAGE_BACKUP" ]; then
  echo "backup files not found for timestamp ${TS}" >&2
  exit 1
fi

cd "$REPO_ROOT/deploy"
docker compose stop backend

cd "$REPO_ROOT"
NOW="$(date +%Y%m%d_%H%M%S)"
# backend/data はコンテナ(root実行)が作成するためroot所有。書き込みにsudoが必要
if [ -f backend/data/smartcloset.db ]; then
  sudo mv backend/data/smartcloset.db "backend/data/smartcloset.db.before_restore_${NOW}"
fi
if [ -d backend/storage ]; then
  mv backend/storage "backend/storage.before_restore_${NOW}"
fi

sudo mkdir -p backend/data
mkdir -p backend/storage
sudo cp "$DB_BACKUP" backend/data/smartcloset.db
tar xzf "$STORAGE_BACKUP" -C backend

cd "$REPO_ROOT/deploy"
docker compose start backend

cd "$REPO_ROOT"
# backend/data はroot所有のため読み取り時のロック確保にもsudoが必要
sudo python3 - "$REPO_ROOT/backend" <<'PYEOF'
import sqlite3
import sys
from pathlib import Path

backend_dir = Path(sys.argv[1])
db_path = backend_dir / "data" / "smartcloset.db"
conn = sqlite3.connect(str(db_path))
cur = conn.execute(
    "SELECT id, original_image_path, transparent_image_path FROM clothing_items"
)
missing = []
for item_id, original_path, transparent_path in cur.fetchall():
    for label, path in (("original", original_path), ("transparent", transparent_path)):
        if not path:
            continue
        full_path = backend_dir / path
        if not full_path.is_file():
            missing.append((item_id, label, str(full_path)))

if missing:
    print(f"[restore] missing files: {len(missing)}")
    for item_id, label, path in missing:
        print(f"  item_id={item_id} kind={label} path={path}")
    sys.exit(1)
print("[restore] verification ok: no missing files")
PYEOF
