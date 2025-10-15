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
    
    # Purchase information - SEPARATE tracking
    purchase_price_yen = db.Column(db.Float, default=0.0)  # From Yuyu-tei at time of purchase
    purchase_price_sgd = db.Column(db.Float, default=0.0)  # Manual input - what you actually paid
    purchase_date = db.Column(db.Date, default=date.today)
    
    # Current market value (Yen from Yuyu-tei, SGD manual/calculated)
    current_price_yen = db.Column(db.Float, default=0.0)    # PRIMARY - from Yuyu-tei (auto-updated)
    current_price_sgd = db.Column(db.Float, default=0.0)    # SECONDARY - manual or calculated
    last_price_update_yen = db.Column(db.DateTime, default=datetime.utcnow)
    last_price_update_sgd = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Tracking preferences
    primary_currency = db.Column(db.String(10), default='YEN')  # YEN or SGD
    track_yen_trends = db.Column(db.Boolean, default=True)      # Focus on Yen price tracking
    track_sgd_trends = db.Column(db.Boolean, default=False)     # Optional SGD tracking
    
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
    
    # Daily price data - SEPARATE tracking
    date_recorded = db.Column(db.Date, nullable=False, default=date.today)
    
    # Yen prices (PRIMARY - from Yuyu-tei)
    price_yen = db.Column(db.Float, nullable=True)           # Live market price from Yuyu-tei
    yen_source = db.Column(db.String(50), default='yuyu-tei') # Always yuyu-tei
    yen_fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # SGD prices (SECONDARY - manual or calculated)
    price_sgd = db.Column(db.Float, nullable=True)           # Manual input or calculated
    sgd_source = db.Column(db.String(50), default='manual')  # 'manual' or 'calculated'
    sgd_updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Exchange rate used ONLY if SGD is calculated from Yen
    jpy_to_sgd_rate = db.Column(db.Float, nullable=True)     # Only used for reference
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        yen_str = f'¥{self.price_yen}' if self.price_yen else 'No Yen'
        sgd_str = f'${self.price_sgd}' if self.price_sgd else 'No SGD'
        return f'<PriceHistory {self.date_recorded}: {yen_str} / {sgd_str}>'

class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_name = db.Column(db.String(150), nullable=False)
    set_name = db.Column(db.String(150))
    target_price_sgd = db.Column(db.Float, default=0.0)
    priority = db.Column(db.String(50), default='Medium')