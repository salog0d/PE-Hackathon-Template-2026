import logging
import tempfile

from flask import Blueprint, jsonify, request

from app.services import user_service
from app.utils.bulk_loader import BulkLoader
from app.utils.serializers import serialize_user

logger = logging.getLogger(__name__)

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.get("/")
def list_users():
    """
    List all users
    ---
    tags:
      - Users
    parameters:
      - name: page
        in: query
        type: integer
        required: false
      - name: per_page
        in: query
        type: integer
        required: false
    responses:
      200:
        description: List of users
    """
    page = request.args.get("page", type=int)
    per_page = request.args.get("per_page", type=int)
    users = user_service.get_all()
    if page is not None and per_page is not None:
        start = (page - 1) * per_page
        users = users[start : start + per_page]
    logger.info("users_listed", extra={"count": len(users)})
    return jsonify([serialize_user(u) for u in users])


@users_bp.get("/<int:user_id>")
def get_user(user_id):
    """
    Get a user by ID
    ---
    tags:
      - Users
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: User found
      404:
        description: User not found
    """
    user = user_service.get_by_id(user_id)
    if not user:
        logger.info("user_not_found", extra={"user_id": user_id})
        return jsonify(error="Not found"), 404
    return jsonify(serialize_user(user))


@users_bp.post("/")
def create_user():
    """
    Create a new user
    ---
    tags:
      - Users
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - username
            - email
          properties:
            username:
              type: string
            email:
              type: string
    responses:
      201:
        description: User created
      400:
        description: Validation error
    """
    data = request.get_json()
    logger.info("user_create_requested", extra={"username": data.get("username")})
    try:
        user = user_service.create(**data)
    except ValueError as e:
        logger.warning("user_create_validation_failed", extra={"reason": str(e)})
        return jsonify(error=str(e)), 400
    logger.info("user_create_succeeded", extra={"user_id": user.id})
    return jsonify(serialize_user(user)), 201


@users_bp.post("/bulk")
def bulk_users():
    """
    Bulk load users from a CSV file
    ---
    tags:
      - Users
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
        logger.warning("bulk_users_no_file")
        return jsonify(error="No file provided"), 400
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        request.files["file"].save(tmp)
        path = tmp.name
    logger.info("bulk_users_started", extra={"path": path})
    count = BulkLoader.load_users(path)
    logger.info("bulk_users_completed", extra={"count": count})
    return jsonify(imported=count, model="users")


@users_bp.route("/<int:user_id>", methods=["PATCH", "PUT"])
def update_user(user_id):
    """
    Update a user
    ---
    tags:
      - Users
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
            email:
              type: string
    responses:
      200:
        description: User updated
      400:
        description: Validation error
      404:
        description: User not found
    """
    data = request.get_json()
    logger.info(
        "user_update_requested", extra={"user_id": user_id, "fields": list(data.keys())}
    )
    try:
        updated = user_service.update(user_id, **data)
    except ValueError as e:
        logger.warning(
            "user_update_validation_failed",
            extra={"user_id": user_id, "reason": str(e)},
        )
        return jsonify(error=str(e)), 400
    if not updated:
        logger.info("user_update_not_found", extra={"user_id": user_id})
        return jsonify(error="Not found"), 404
    logger.info("user_update_succeeded", extra={"user_id": user_id})
    return jsonify(serialize_user(user_service.get_by_id(user_id)))


@users_bp.delete("/<int:user_id>")
def delete_user(user_id):
    """
    Delete a user
    ---
    tags:
      - Users
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      204:
        description: User deleted
      404:
        description: User not found
    """
    logger.info("user_delete_requested", extra={"user_id": user_id})
    if not user_service.delete(user_id):
        logger.info("user_delete_not_found", extra={"user_id": user_id})
        return jsonify(error="user not found"), 404
    logger.info("user_delete_succeeded", extra={"user_id": user_id})
    return "", 204
