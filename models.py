# models.py
from flask_sqlalchemy import SQLAlchemy # Import SQLAlchemy here
from sqlalchemy.sql import func # Import func for default date/timestamp

db = SQLAlchemy() # Define db instance here

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    set_name = db.Column(db.String(100))
    card_number = db.Column(db.String(20))
    rarity = db.Column(db.String(50))
    color = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1)
    purchase_price_sgd = db.Column(db.Float)
    purchase_date = db.Column(db.Date, default=func.current_timestamp())
    image_url = db.Column(db.String(200))
    current_value_sgd = db.Column(db.Float)

    expenses = db.relationship('Expense', backref='card', lazy=True)

    def __repr__(self):
        return f'<Card {self.name} ({self.set_name})>'

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount_sgd = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100))
    expense_date = db.Column(db.Date, default=func.current_timestamp())
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'), nullable=True)

    def __repr__(self):
        return f'<Expense {self.description}: {self.amount_sgd}>'

class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_name = db.Column(db.String(100), nullable=False)
    set_name = db.Column(db.String(100))
    target_price_sgd = db.Column(db.Float)
    priority = db.Column(db.String(50))

    def __repr__(self):
        return f'<Wishlist: {self.card_name}>'