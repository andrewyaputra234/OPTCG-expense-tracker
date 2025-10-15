"""
Test script to add sample cards to inventory for demonstration
"""

import os
from app import create_app
from models import db, InventoryCard, PriceHistory
from datetime import date, datetime

# Sample cards to add
SAMPLE_CARDS = [
    {
        'card_number': 'OP01-025',
        'name': 'Monkey D. Luffy',
        'rarity': 'SR',
        'purchase_price_yen': 800,
        'purchase_price_sgd': 7.20,
        'quantity': 1,
        'condition': 'Near Mint'
    },
    {
        'card_number': 'OP01-121',
        'name': 'Yamato',
        'rarity': 'SEC',
        'purchase_price_yen': 1200,
        'purchase_price_sgd': 10.80,
        'quantity': 1,
        'condition': 'Near Mint'
    },
    {
        'card_number': 'OP01-001',
        'name': 'Roronoa Zoro',
        'rarity': 'L',
        'purchase_price_yen': 300,
        'purchase_price_sgd': 2.70,
        'quantity': 2,
        'condition': 'Lightly Played'
    }
]

def add_sample_cards():
    """Add sample cards to inventory for testing"""
    app = create_app()
    
    with app.app_context():
        print("Adding sample cards to inventory...")
        
        for card_data in SAMPLE_CARDS:
            # Check if card already exists
            existing_card = InventoryCard.query.filter_by(
                card_number=card_data['card_number']
            ).first()
            
            if existing_card:
                print(f"  {card_data['card_number']} already exists, skipping...")
                continue
            
            # Create new inventory card
            new_card = InventoryCard(
                name=card_data['name'],
                card_number=card_data['card_number'],
                rarity=card_data['rarity'],
                quantity=card_data['quantity'],
                purchase_price_yen=card_data['purchase_price_yen'],
                purchase_price_sgd=card_data['purchase_price_sgd'],
                current_price_yen=card_data['purchase_price_yen'],  # Start with purchase price
                current_price_sgd=card_data['purchase_price_sgd'],
                condition=card_data['condition'],
                last_price_update=datetime.utcnow()
            )
            
            db.session.add(new_card)
            db.session.flush()  # Get the ID
            
            # Add initial price history entry
            price_entry = PriceHistory(
                inventory_card_id=new_card.id,
                price_yen=card_data['purchase_price_yen'],
                price_sgd=card_data['purchase_price_sgd']
            )
            
            db.session.add(price_entry)
            
            print(f"  Added {card_data['card_number']}: {card_data['name']}")
        
        try:
            db.session.commit()
            print("\n✅ Sample cards added successfully!")
            
            # Show inventory summary
            cards = InventoryCard.query.all()
            total_cards = sum(card.quantity for card in cards)
            total_value = sum(card.current_price_sgd * card.quantity for card in cards)
            
            print(f"\nInventory Summary:")
            print(f"  Total cards: {total_cards}")
            print(f"  Unique cards: {len(cards)}")
            print(f"  Total value: ${total_value:.2f} SGD")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding sample cards: {e}")

if __name__ == "__main__":
    add_sample_cards()