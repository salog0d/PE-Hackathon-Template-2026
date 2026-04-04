from importlib import import_module

from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask, jsonify

from app.database import check_db, init_db
from app.api import register_routes


def create_app():
    load_dotenv()

    app = Flask(__name__)

    Swagger(app, template={"info": {"title": "URL Shortener API", "version": "1.0"}})

    init_db(app)

    import_module("app.models")

    register_routes(app)

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
