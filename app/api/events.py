from flask import Blueprint, jsonify, request

from app.services import event_service
from app.utils.serializers import serialize_event

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
    responses:
      200:
        description: List of events
    """
    url_id = request.args.get("url_id", type=int)
    user_id = request.args.get("user_id", type=int)
    if url_id:
        return jsonify([serialize_event(e) for e in event_service.get_by_url(url_id)])
    if user_id:
        return jsonify([serialize_event(e) for e in event_service.get_by_user(user_id)])
    return jsonify([serialize_event(e) for e in event_service.get_all()])


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
        return jsonify(error="Not found"), 404
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
    try:
        event = event_service.create(**data)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    return jsonify(serialize_event(event)), 201


@events_bp.patch("/<int:event_id>")
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
    try:
        updated = event_service.update(event_id, **data)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    if not updated:
        return jsonify(error="Not found"), 404
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
    if not event_service.delete(event_id):
        return jsonify(error="Not found"), 404
    return "", 204
