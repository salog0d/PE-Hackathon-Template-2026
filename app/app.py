import logging
import time
import uuid
from importlib import import_module

from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask, g, jsonify, request

from app.api import register_routes
from app.database import check_db, init_db
from app.logging_config import request_id_var, setup_logging

logger = logging.getLogger(__name__)


def create_app():
    load_dotenv()
    setup_logging()

    app = Flask(__name__)

    Swagger(app, template={"info": {"title": "URL Shortener API", "version": "1.0"}})

    init_db(app)

    import_module("app.models")

    register_routes(app)

    # ------------------------------------------------------------------ #
    # Request tracing middleware                                           #
    # ------------------------------------------------------------------ #

    @app.before_request
    def _set_request_context():
        request_id = str(uuid.uuid4())
        g.request_id = request_id
        g.request_start = time.perf_counter()
        request_id_var.set(request_id)
        logger.info(
            "request_started",
            extra={"method": request.method, "path": request.path},
        )

    @app.after_request
    def _log_response(response):
        latency_ms = round((time.perf_counter() - g.request_start) * 1000, 2)
        logger.info(
            "request_finished",
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response

    # ------------------------------------------------------------------ #
    # Global exception handler                                            #
    # ------------------------------------------------------------------ #

    @app.errorhandler(Exception)
    def _handle_unexpected_error(exc):
        logger.exception("unexpected_error")
        return jsonify(error="internal server error"), 500

    # ------------------------------------------------------------------ #
    # Health endpoints                                                     #
    # ------------------------------------------------------------------ #

    @app.route("/health")
    def health():
        """
        Basic liveness probe — always returns 200 if the process is up.
        ---
        tags:
          - Health
        responses:
          200:
            description: Process is alive
        """
        return jsonify(status="ok")
    
    @app.route("/favicon.ico")
    def favicon():
        return "", 204

    @app.route("/health/db")
    def health_db():
        """
        Readiness probe — checks live DB connectivity.

        Returns 200 when the database is reachable, or 503 (with an error
        message) when it is not.  Use this endpoint to demonstrate recovery:
        stop the DB, hit this endpoint to confirm the failure, restart the DB,
        then hit again to confirm automatic reconnection.
        ---
        tags:
          - Health
        responses:
          200:
            description: Database is reachable
          503:
            description: Database is unreachable
        """
        result = check_db()
        if result["ok"]:
            return jsonify(status="ok", database="reachable")
        return jsonify(
            status="degraded", database="unreachable", error=result["error"]
        ), 503

    return app
