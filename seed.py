"""Run with: python seed.py"""

import logging

from app.app import create_app
from app.utils.bulk_loader import BulkLoader

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

app = create_app()

with app.app_context():
    result = BulkLoader.load_all(
        users_path="seeds/users.csv",
        urls_path="seeds/urls.csv",
        events_path="seeds/events.csv",
    )
    print(result)
