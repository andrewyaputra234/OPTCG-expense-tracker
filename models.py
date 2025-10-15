# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime

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

    # New foreign key to link to a Collection
    collection_id = db.Column(db.Integer, db.ForeignKey('collection.id'), nullable=True)

# New models for inventory tracking with daily price monitoring
class InventoryCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    set_name = db.Column(db.String(150))
    card_number = db.Column(db.String(20), nullable=False)
    rarity = db.Column(db.String(50))
    color = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1)
    
    # Purchase information
    purchase_price_yen = db.Column(db.Float, default=0.0)
    purchase_price_sgd = db.Column(db.Float, default=0.0)
    purchase_date = db.Column(db.Date, default=date.today)
    
    # Current market value (updated daily)
    current_price_yen = db.Column(db.Float, default=0.0)
    current_price_sgd = db.Column(db.Float, default=0.0)
    last_price_update = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Additional info
    condition = db.Column(db.String(50), default='Near Mint')  # NM, LP, MP, HP, etc.
    notes = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    
    # Relationships
    price_history = db.relationship('PriceHistory', backref='inventory_card', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<InventoryCard {self.card_number}: {self.name}>'

class PriceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventory_card_id = db.Column(db.Integer, db.ForeignKey('inventory_card.id'), nullable=False)
    
    # Daily price data
    date_recorded = db.Column(db.Date, nullable=False, default=date.today)
    price_yen = db.Column(db.Float, nullable=False)
    price_sgd = db.Column(db.Float, nullable=False)
    
    # Exchange rate used for conversion
    jpy_to_sgd_rate = db.Column(db.Float, default=0.009)  # Approximate rate
    
    # Source information
    source = db.Column(db.String(50), default='yuyu-tei')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PriceHistory {self.date_recorded}: ¥{self.price_yen} / ${self.price_sgd}>'

class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_name = db.Column(db.String(150), nullable=False)
    set_name = db.Column(db.String(150))
    target_price_sgd = db.Column(db.Float, default=0.0)
    priority = db.Column(db.String(50), default='Medium')