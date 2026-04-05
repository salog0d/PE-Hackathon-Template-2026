import logging

from flask import Blueprint, jsonify, redirect, request

from app.metrics import urls_created_total
from app.services import url_service
from app.utils.serializers import serialize_url

logger = logging.getLogger(__name__)

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
      - name: is_active
        in: query
        type: boolean
        required: false
        description: Filter by active status
    responses:
      200:
        description: List of URLs
    """
    user_id = request.args.get("user_id", type=int)
    is_active_str = request.args.get("is_active")

    if user_id:
        urls = url_service.get_by_user(user_id)
        logger.info(
            "urls_listed_by_user", extra={"user_id": user_id, "count": len(urls)}
        )
    else:
        urls = url_service.get_all()
        logger.info("urls_listed", extra={"count": len(urls)})

    if is_active_str is not None:
        is_active = is_active_str.lower() in ("true", "1", "yes")
        urls = [u for u in urls if u.is_active == is_active]

    return jsonify([serialize_url(u) for u in urls])


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
        logger.info("url_not_found", extra={"url_id": url_id})
        return jsonify(error="url not found"), 404
    return jsonify(serialize_url(url))


@urls_bp.get("/<string:short_code>/redirect")
def redirect_short_code(short_code):
    """
    Redirect to the original URL for a given short code
    ---
    tags:
      - URLs
    parameters:
      - name: short_code
        in: path
        type: string
        required: true
    responses:
      301:
        description: Redirect to original URL
      404:
        description: URL not found
    """
    url = url_service.get_by_short_code(short_code)
    if not url:
        logger.info("url_redirect_not_found", extra={"short_code": short_code})
        return jsonify(error="url not found"), 404
    logger.info(
        "url_redirecting",
        extra={"short_code": short_code, "original_url": url.original_url},
    )
    return redirect(url.original_url, code=301)


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
        logger.info("url_not_found_by_code", extra={"short_code": short_code})
        return jsonify(error="url not found"), 404
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
    logger.info(
        "url_create_requested",
        extra={"user_id": data.get("user_id"), "short_code": data.get("short_code")},
    )
    try:
        url = url_service.create(**data)
    except ValueError as e:
        logger.warning("url_create_validation_failed", extra={"reason": str(e)})
        return jsonify(error=str(e)), 400
    urls_created_total.inc()
    logger.info("url_create_succeeded", extra={"url_id": url.id})
    return jsonify(serialize_url(url)), 201


@urls_bp.route("/<int:url_id>", methods=["PATCH", "PUT"])
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
    logger.info(
        "url_update_requested", extra={"url_id": url_id, "fields": list(data.keys())}
    )
    try:
        updated = url_service.update(url_id, **data)
    except ValueError as e:
        logger.warning(
            "url_update_validation_failed", extra={"url_id": url_id, "reason": str(e)}
        )
        return jsonify(error=str(e)), 400
    if not updated:
        logger.info("url_update_not_found", extra={"url_id": url_id})
        return jsonify(error="url not found"), 404
    logger.info("url_update_succeeded", extra={"url_id": url_id})
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
    logger.info("url_delete_requested", extra={"url_id": url_id})
    if not url_service.delete(url_id):
        logger.info("url_delete_not_found", extra={"url_id": url_id})
        return jsonify(error="url not found"), 404
    logger.info("url_delete_succeeded", extra={"url_id": url_id})
    return "", 204
