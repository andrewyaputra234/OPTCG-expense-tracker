from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY='dev',
        SQLALCHEMY_DATABASE_URI='sqlite:///one_piece_tcg.sqlite'
    )

    db.init_app(app)

    with app.app_context():
        # Import models here to register them with SQLAlchemy
        from . import models

        db.create_all()

    return app