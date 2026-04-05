"""
Usage:
  python migrate.py create <name>   # create a new migration
  python migrate.py run             # apply all pending migrations
  python migrate.py rollback        # revert the last migration
"""

import sys

from dotenv import load_dotenv
from peewee_migrate import Router

from app.app import create_app
from app.database import db

load_dotenv()

app = create_app()

with app.app_context():
    db.connect(reuse_if_open=True)
    router = Router(db, migrate_dir="app/database/migrations")

    command = sys.argv[1] if len(sys.argv) > 1 else None

    if command == "create":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        if not name:
            print("Usage: python migrate.py create <name>")
            sys.exit(1)
        router.create(name, auto=True)

    elif command == "run":
        router.run()

    elif command == "rollback":
        router.rollback()

    else:
        print(__doc__)
        sys.exit(1)
