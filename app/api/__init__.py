def register_routes(app):
    from app.api.users import users_bp
    from app.api.urls import urls_bp
    from app.api.events import events_bp
    from app.api.seed import seed_bp

    app.register_blueprint(users_bp)
    app.register_blueprint(urls_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(seed_bp)
