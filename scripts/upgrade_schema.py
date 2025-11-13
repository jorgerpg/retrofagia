#!/usr/bin/env python3
"""Ensure database schema has latest columns required by the app."""

from pathlib import Path
from textwrap import dedent
import subprocess

import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import text

from app import create_app, db


STATEMENTS = (
    """
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
    """,
    """
    ALTER TABLE albums
    ADD COLUMN IF NOT EXISTS personal_cover_url VARCHAR(512) NOT NULL DEFAULT '';
    """,
)


def main() -> int:
    app = create_app()
    with app.app_context():
        for statement in STATEMENTS:
            sql = text(dedent(statement).strip())
            db.session.execute(sql)
        db.session.commit()
    print("Schema atualizado com sucesso.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--docker":
        try:
            subprocess.run(
                ["docker", "compose", "exec", "web", "python", "scripts/upgrade_schema.py"],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            sys.exit(exc.returncode)
        sys.exit(0)

    raise SystemExit(main())
