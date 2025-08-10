from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI='sqlite:///one_piece_tcg.sqlite',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)

    # Import models to register with SQLAlchemy
    with app.app_context():
        from . import models
        db.create_all()

    # Import and register blueprints (outside app_context is fine)
    from .collections import collections_bp
    from .cards import cards_bp
    from .divisor import divisor_bp

    app.register_blueprint(collections_bp, url_prefix='/collections')
    app.register_blueprint(cards_bp, url_prefix='/cards')
    app.register_blueprint(divisor_bp, url_prefix='/divisor')

    @app.before_request
    def before_request():
        g.messages = []

    @app.context_processor
    def inject_today_date():
        from datetime import date
        return {'today_date': date.today().isoformat()}

    @app.route('/')
    def index():
        return "Welcome to the One Piece TCG app!"

    return app
