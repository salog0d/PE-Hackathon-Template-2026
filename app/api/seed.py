import logging
import tempfile

from flask import Blueprint, jsonify, request

from app.utils.bulk_loader import BulkLoader

logger = logging.getLogger(__name__)

seed_bp = Blueprint("seed", __name__, url_prefix="/seed")


def _save_temp(file) -> str:
    suffix = ".csv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file.save(tmp)
        return tmp.name


@seed_bp.post("/users")
def seed_users():
    """
    Bulk load users from a CSV file
    ---
    tags:
      - Seed
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: CSV file with columns id, username, email, created_at
    responses:
      200:
        description: Users loaded successfully
      400:
        description: No file provided
    """
    if "file" not in request.files:
        logger.warning("seed_users_no_file")
        return jsonify(error="No file provided"), 400
    path = _save_temp(request.files["file"])
    logger.info("seed_users_started", extra={"path": path})
    count = BulkLoader.load_users(path)
    logger.info("seed_users_completed", extra={"count": count})
    return jsonify(loaded=count, model="users")


@seed_bp.post("/urls")
def seed_urls():
    """
    Bulk load URLs from a CSV file
    ---
    tags:
      - Seed
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: CSV file with columns id, user_id, short_code, original_url, title, is_active, created_at, updated_at
    responses:
      200:
        description: URLs loaded successfully
      400:
        description: No file provided
    """
    if "file" not in request.files:
        logger.warning("seed_urls_no_file")
        return jsonify(error="No file provided"), 400
    path = _save_temp(request.files["file"])
    logger.info("seed_urls_started", extra={"path": path})
    count = BulkLoader.load_urls(path)
    logger.info("seed_urls_completed", extra={"count": count})
    return jsonify(loaded=count, model="urls")


@seed_bp.post("/events")
def seed_events():
    """
    Bulk load events from a CSV file
    ---
    tags:
      - Seed
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: CSV file with columns id, url_id, user_id, event_type, timestamp, details
    responses:
      200:
        description: Events loaded successfully
      400:
        description: No file provided
    """
    if "file" not in request.files:
        logger.warning("seed_events_no_file")
        return jsonify(error="No file provided"), 400
    path = _save_temp(request.files["file"])
    logger.info("seed_events_started", extra={"path": path})
    count = BulkLoader.load_events(path)
    logger.info("seed_events_completed", extra={"count": count})
    return jsonify(loaded=count, model="events")
