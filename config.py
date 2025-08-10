import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///instance/one_piece_tcg.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
