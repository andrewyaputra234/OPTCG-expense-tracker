# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import date

db = SQLAlchemy()

class Collection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text)
    cards = db.relationship('Card', backref='collection', lazy=True)

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    set_name = db.Column(db.String(150))
    card_number = db.Column(db.String(20))
    rarity = db.Column(db.String(50))
    color = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1)
    
    purchase_price_original = db.Column(db.Float, default=0.0)
    original_currency = db.Column(db.String(10), default='SGD')
    purchase_price_sgd = db.Column(db.Float, default=0.0)
    current_value_sgd = db.Column(db.Float, default=0.0)
    image_url = db.Column(db.String(500))
    purchase_date = db.Column(db.Date, default=date.today)

    expenses = db.relationship('Expense', backref='card', lazy=True)

    # New foreign key to link to a Collection
    collection_id = db.Column(db.Integer, db.ForeignKey('collection.id'), nullable=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(250), nullable=False)
    amount_sgd = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'), nullable=True)

class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_name = db.Column(db.String(150), nullable=False)
    set_name = db.Column(db.String(150))
    target_price_sgd = db.Column(db.Float, default=0.0)
    priority = db.Column(db.String(50), default='Medium')