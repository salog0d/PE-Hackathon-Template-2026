from flask import Blueprint, jsonify, request

from app.services import user_service
from app.utils.serializers import serialize_user

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.get("/")
def list_users():
    """
    List all users
    ---
    tags:
      - Users
    responses:
      200:
        description: List of users
    """
    return jsonify([serialize_user(u) for u in user_service.get_all()])


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
    try:
        user = user_service.create(**data)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    return jsonify(serialize_user(user)), 201


@users_bp.patch("/<int:user_id>")
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
    try:
        updated = user_service.update(user_id, **data)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    if not updated:
        return jsonify(error="Not found"), 404
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
    if not user_service.delete(user_id):
        return jsonify(error="Not found"), 404
    return "", 204
