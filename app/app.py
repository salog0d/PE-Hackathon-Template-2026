from importlib import import_module

from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask, jsonify

from app.database import init_db
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
        return jsonify(status="ok")

    return app
