#!/usr/bin/env python
"""Promote a user to admin by email."""

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app, db
from app.models import User


def promote(email: str) -> int:
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"Usuário com email {email} não encontrado.")
            return 1
        if user.is_admin:
            print(f"{email} já é admin.")
            return 0
        user.is_admin = True
        db.session.commit()
        print(f"{email} promovido a admin.")
        return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python scripts/promote_to_admin.py <email>")
        sys.exit(1)
    sys.exit(promote(sys.argv[1]))
