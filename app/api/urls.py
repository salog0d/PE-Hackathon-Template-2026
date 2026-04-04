from flask import Blueprint, jsonify, request

from app.services import url_service
from app.utils.serializers import serialize_url

urls_bp = Blueprint("urls", __name__, url_prefix="/urls")


@urls_bp.get("/")
def list_urls():
    """
    List all URLs
    ---
    tags:
      - URLs
    parameters:
      - name: user_id
        in: query
        type: integer
        required: false
        description: Filter by user ID
    responses:
      200:
        description: List of URLs
    """
    user_id = request.args.get("user_id", type=int)
    if user_id:
        return jsonify([serialize_url(u) for u in url_service.get_by_user(user_id)])
    return jsonify([serialize_url(u) for u in url_service.get_all()])


@urls_bp.get("/<int:url_id>")
def get_url(url_id):
    """
    Get a URL by ID
    ---
    tags:
      - URLs
    parameters:
      - name: url_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: URL found
      404:
        description: URL not found
    """
    url = url_service.get_by_id(url_id)
    if not url:
        return jsonify(error="Not found"), 404
    return jsonify(serialize_url(url))


@urls_bp.get("/code/<string:short_code>")
def get_by_short_code(short_code):
    """
    Get a URL by short code
    ---
    tags:
      - URLs
    parameters:
      - name: short_code
        in: path
        type: string
        required: true
    responses:
      200:
        description: URL found
      404:
        description: URL not found
    """
    url = url_service.get_by_short_code(short_code)
    if not url:
        return jsonify(error="Not found"), 404
    return jsonify(serialize_url(url))


@urls_bp.post("/")
def create_url():
    """
    Create a new short URL
    ---
    tags:
      - URLs
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - user_id
            - short_code
            - original_url
          properties:
            user_id:
              type: integer
            short_code:
              type: string
            original_url:
              type: string
            title:
              type: string
            is_active:
              type: boolean
    responses:
      201:
        description: URL created
      400:
        description: Validation error
    """
    data = request.get_json()
    try:
        url = url_service.create(**data)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    return jsonify(serialize_url(url)), 201


@urls_bp.patch("/<int:url_id>")
def update_url(url_id):
    """
    Update a URL
    ---
    tags:
      - URLs
    parameters:
      - name: url_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            short_code:
              type: string
            original_url:
              type: string
            title:
              type: string
            is_active:
              type: boolean
    responses:
      200:
        description: URL updated
      400:
        description: Validation error
      404:
        description: URL not found
    """
    data = request.get_json()
    try:
        updated = url_service.update(url_id, **data)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    if not updated:
        return jsonify(error="Not found"), 404
    return jsonify(serialize_url(url_service.get_by_id(url_id)))


@urls_bp.delete("/<int:url_id>")
def delete_url(url_id):
    """
    Delete a URL
    ---
    tags:
      - URLs
    parameters:
      - name: url_id
        in: path
        type: integer
        required: true
    responses:
      204:
        description: URL deleted
      404:
        description: URL not found
    """
    if not url_service.delete(url_id):
        return jsonify(error="Not found"), 404
    return "", 204
