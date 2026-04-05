import json
import logging

from flask import Blueprint, jsonify, request

from app.services import event_service
from app.utils.serializers import serialize_event

logger = logging.getLogger(__name__)

events_bp = Blueprint("events", __name__, url_prefix="/events")


@events_bp.get("/")
def list_events():
    """
    List all events
    ---
    tags:
      - Events
    parameters:
      - name: url_id
        in: query
        type: integer
        required: false
        description: Filter by URL ID
      - name: user_id
        in: query
        type: integer
        required: false
        description: Filter by user ID
      - name: event_type
        in: query
        type: string
        required: false
        description: Filter by event type
    responses:
      200:
        description: List of events
    """
    url_id = request.args.get("url_id", type=int)
    user_id = request.args.get("user_id", type=int)
    event_type = request.args.get("event_type")

    if url_id:
        events = event_service.get_by_url(url_id)
        logger.info(
            "events_listed_by_url", extra={"url_id": url_id, "count": len(events)}
        )
    elif user_id:
        events = event_service.get_by_user(user_id)
        logger.info(
            "events_listed_by_user", extra={"user_id": user_id, "count": len(events)}
        )
    elif event_type:
        events = event_service.get_by_event_type(event_type)
        logger.info(
            "events_listed_by_type",
            extra={"event_type": event_type, "count": len(events)},
        )
    else:
        events = event_service.get_all()
        logger.info("events_listed", extra={"count": len(events)})

    return jsonify([serialize_event(e) for e in events])


@events_bp.get("/<int:event_id>")
def get_event(event_id):
    """
    Get an event by ID
    ---
    tags:
      - Events
    parameters:
      - name: event_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Event found
      404:
        description: Event not found
    """
    event = event_service.get_by_id(event_id)
    if not event:
        logger.info("event_not_found", extra={"event_id": event_id})
        return jsonify(error="event not found"), 404
    return jsonify(serialize_event(event))


@events_bp.post("/")
def create_event():
    """
    Create a new event
    ---
    tags:
      - Events
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - url_id
            - user_id
            - event_type
          properties:
            url_id:
              type: integer
            user_id:
              type: integer
            event_type:
              type: string
            details:
              type: string
    responses:
      201:
        description: Event created
      400:
        description: Validation error
    """
    data = request.get_json()
    # Stringify details if it arrives as a JSON object
    if isinstance(data.get("details"), dict):
        data = dict(data, details=json.dumps(data["details"]))
    logger.info(
        "event_create_requested",
        extra={
            "url_id": data.get("url_id"),
            "user_id": data.get("user_id"),
            "event_type": data.get("event_type"),
        },
    )
    try:
        event = event_service.create(**data)
    except ValueError as e:
        logger.warning("event_create_validation_failed", extra={"reason": str(e)})
        return jsonify(error=str(e)), 400
    logger.info("event_create_succeeded", extra={"event_id": event.id})
    return jsonify(serialize_event(event)), 201


@events_bp.route("/<int:event_id>", methods=["PATCH", "PUT"])
def update_event(event_id):
    """
    Update an event
    ---
    tags:
      - Events
    parameters:
      - name: event_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            event_type:
              type: string
            details:
              type: string
    responses:
      200:
        description: Event updated
      400:
        description: Validation error
      404:
        description: Event not found
    """
    data = request.get_json()
    if isinstance(data.get("details"), dict):
        data = dict(data, details=json.dumps(data["details"]))
    logger.info(
        "event_update_requested",
        extra={"event_id": event_id, "fields": list(data.keys())},
    )
    try:
        updated = event_service.update(event_id, **data)
    except ValueError as e:
        logger.warning(
            "event_update_validation_failed",
            extra={"event_id": event_id, "reason": str(e)},
        )
        return jsonify(error=str(e)), 400
    if not updated:
        logger.info("event_update_not_found", extra={"event_id": event_id})
        return jsonify(error="event not found"), 404
    logger.info("event_update_succeeded", extra={"event_id": event_id})
    return jsonify(serialize_event(event_service.get_by_id(event_id)))


@events_bp.delete("/<int:event_id>")
def delete_event(event_id):
    """
    Delete an event
    ---
    tags:
      - Events
    parameters:
      - name: event_id
        in: path
        type: integer
        required: true
    responses:
      204:
        description: Event deleted
      404:
        description: Event not found
    """
    logger.info("event_delete_requested", extra={"event_id": event_id})
    if not event_service.delete(event_id):
        logger.info("event_delete_not_found", extra={"event_id": event_id})
        return jsonify(error="event not found"), 404
    logger.info("event_delete_succeeded", extra={"event_id": event_id})
    return "", 204
