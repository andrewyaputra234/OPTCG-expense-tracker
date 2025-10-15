"""
Daily price update service for inventory tracking
This script should be run daily to update card prices and maintain price history
"""

import os
import sys
from datetime import date, datetime
from app import create_app
from models import db, InventoryCard, PriceHistory
from chatbot_service import get_yuyutei_prices_by_card_number

# Exchange rate (updated to more current rate)  
JPY_TO_SGD_RATE = 0.0086  # More accurate JPY to SGD rate as of 2024/2025

def update_all_card_prices():
    """Update prices for all inventory cards and add to price history"""
    app = create_app()
    
    with app.app_context():
        cards = InventoryCard.query.all()
        updated_count = 0
        error_count = 0
        
        print(f"Starting price update for {len(cards)} cards...")
        
        for card in cards:
            try:
                # Skip miscellaneous cards (no Yuyu-tei pricing)
                if card.category == 'Miscellaneous':
                    print(f"Skipping {card.card_number}: {card.name} (Miscellaneous - manual pricing only)")
                    continue
                
                # Skip cards with manual price override
                if card.is_manual_override:
                    print(f"Skipping {card.card_number}: {card.name} (Manual price override active)")
                    continue
                    
                print(f"Updating {card.card_number}: {card.name}...")
                
                # Fetch current price from Yuyu-tei (get all variants)
                price_data = get_yuyutei_prices_by_card_number(card.card_number)
                
                if price_data and len(price_data) > 0:
                    # Filter for reasonable prices - higher upper limit for Manga cards
                    if card.category == 'Mangas':
                        # Manga cards can be very expensive (up to ¥500,000+)
                        valid_prices = [p for p in price_data if 50 <= p.get('price_yen', 0) <= 1000000]
                        print(f"  Manga card: Using extended price range (¥50 - ¥1,000,000)")
                    else:
                        # Regular cards: more conservative range
                        valid_prices = [p for p in price_data if 50 <= p.get('price_yen', 0) <= 100000]
                    
                    if valid_prices:
                        # Priority order for highest price selection:
                        # 1. Mangas (ALWAYS highest price - top priority)
                        # 2. SP (second highest value)
                        # 3. Others use first result
                        if card.category == 'Mangas':
                            # Manga cards ALWAYS get the absolute highest price
                            print(f"  📚 MANGA CARD PROCESSING:")
                            print(f"     Found {len(valid_prices)} valid price options:")
                            for i, price_option in enumerate(sorted(valid_prices, key=lambda x: x.get('price_yen', 0), reverse=True)):
                                print(f"     #{i+1}: ¥{price_option.get('price_yen', 0):,} - {price_option.get('name', 'Unknown')}")
                            
                            selected_card = max(valid_prices, key=lambda x: x.get('price_yen', 0))
                            current_price_yen = selected_card.get('price_yen', 0)
                            print(f"  ✅ SELECTED HIGHEST: ¥{current_price_yen:,} - {selected_card.get('name', 'Unknown')}")
                        elif card.category == 'SP':
                            # SP cards get highest price
                            selected_card = max(valid_prices, key=lambda x: x.get('price_yen', 0))
                            current_price_yen = selected_card.get('price_yen', 0)
                        else:
                            current_price_yen = valid_prices[0].get('price_yen', 0)
                        current_price_sgd = current_price_yen * JPY_TO_SGD_RATE
                    else:
                        print(f"  ❌ NO VALID PRICES found for {card.card_number}")
                        print(f"     Raw price data returned: {len(price_data)} results")
                        for i, raw_price in enumerate(price_data[:3]):  # Show first 3 results
                            price_val = raw_price.get('price_yen', 0)
                            price_name = raw_price.get('name', 'Unknown')
                            if card.category == 'Mangas':
                                in_range = 50 <= price_val <= 1000000
                            else:
                                in_range = 50 <= price_val <= 100000
                            print(f"     #{i+1}: ¥{price_val:,} - {price_name} [{'✅' if in_range else '❌ OUT OF RANGE'}]")
                        error_count += 1
                        continue
                    
                    # Update card's current price
                    card.current_price_yen = current_price_yen
                    card.current_price_sgd = current_price_sgd
                    card.last_price_update = datetime.utcnow()
                    
                    # Check if we already have a price entry for today
                    today_entry = PriceHistory.query.filter_by(
                        inventory_card_id=card.id,
                        date_recorded=date.today()
                    ).first()
                    
                    if today_entry:
                        # Update today's entry
                        today_entry.price_yen = current_price_yen
                        today_entry.price_sgd = current_price_sgd
                        today_entry.jpy_to_sgd_rate = JPY_TO_SGD_RATE
                        print(f"  Updated existing entry: ¥{current_price_yen} / ${current_price_sgd:.2f}")
                    else:
                        # Create new price history entry
                        price_entry = PriceHistory(
                            inventory_card_id=card.id,
                            price_yen=current_price_yen,
                            price_sgd=current_price_sgd,
                            jpy_to_sgd_rate=JPY_TO_SGD_RATE
                        )
                        db.session.add(price_entry)
                        print(f"  Added new entry: ¥{current_price_yen} / ${current_price_sgd:.2f}")
                    
                    updated_count += 1
                else:
                    print(f"  ❌ NO PRICE DATA found on Yuyu-tei for {card.card_number}")
                    print(f"     This could mean:")
                    print(f"     - Card not available on Yuyu-tei")
                    print(f"     - Card number format not recognized")
                    print(f"     - Yuyu-tei website connection issues")
                    error_count += 1
                    
            except Exception as e:
                print(f"  Error updating {card.card_number}: {e}")
                error_count += 1
                continue
        
        try:
            db.session.commit()
            print(f"\nPrice update completed!")
            print(f"Successfully updated: {updated_count} cards")
            print(f"Errors: {error_count} cards")
            print(f"Total cards: {len(cards)}")
            
            # Clean up old price history (keep only last 90 days)
            cleanup_old_price_history()
            
        except Exception as e:
            db.session.rollback()
            print(f"Error committing changes: {e}")
            return False
    
    return True

def cleanup_old_price_history(days_to_keep=90):
    """Remove price history older than specified days"""
    from datetime import timedelta
    
    cutoff_date = date.today() - timedelta(days=days_to_keep)
    
    try:
        old_entries = PriceHistory.query.filter(
            PriceHistory.date_recorded < cutoff_date
        ).count()
        
        if old_entries > 0:
            PriceHistory.query.filter(
                PriceHistory.date_recorded < cutoff_date
            ).delete()
            
            db.session.commit()
            print(f"Cleaned up {old_entries} old price history entries (older than {days_to_keep} days)")
        else:
            print("No old price history entries to clean up")
            
    except Exception as e:
        db.session.rollback()
        print(f"Error during cleanup: {e}")

def get_price_update_summary():
    """Get a summary of the current inventory and recent price changes"""
    app = create_app()
    
    with app.app_context():
        cards = InventoryCard.query.all()
        
        if not cards:
            print("No cards in inventory")
            return
        
        total_purchase_value = sum(card.purchase_price_sgd * card.quantity for card in cards)
        total_current_value = sum(card.current_price_sgd * card.quantity for card in cards)
        total_gain_loss = total_current_value - total_purchase_value
        total_gain_loss_percentage = (total_gain_loss / total_purchase_value * 100) if total_purchase_value > 0 else 0
        
        print(f"\n=== INVENTORY SUMMARY ===")
        print(f"Total cards: {sum(card.quantity for card in cards)}")
        print(f"Unique cards: {len(cards)}")
        print(f"Total invested: ${total_purchase_value:.2f}")
        print(f"Current value: ${total_current_value:.2f}")
        print(f"P&L: ${total_gain_loss:+.2f} ({total_gain_loss_percentage:+.1f}%)")
        
        # Show top gainers and losers
        card_performances = []
        for card in cards:
            if card.purchase_price_sgd > 0:
                gain_loss_percentage = (card.current_price_sgd - card.purchase_price_sgd) / card.purchase_price_sgd * 100
                card_performances.append({
                    'card': card,
                    'gain_loss_percentage': gain_loss_percentage
                })
        
        if card_performances:
            card_performances.sort(key=lambda x: x['gain_loss_percentage'], reverse=True)
            
            print(f"\nTop 3 performers:")
            for i, performance in enumerate(card_performances[:3]):
                card = performance['card']
                pct = performance['gain_loss_percentage']
                print(f"  {i+1}. {card.name} ({card.card_number}): {pct:+.1f}%")
            
            print(f"\nBottom 3 performers:")
            for i, performance in enumerate(card_performances[-3:]):
                card = performance['card']
                pct = performance['gain_loss_percentage']
                print(f"  {i+1}. {card.name} ({card.card_number}): {pct:+.1f}%")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "update":
            update_all_card_prices()
        elif sys.argv[1] == "summary":
            get_price_update_summary()
        else:
            print("Usage: python price_updater.py [update|summary]")
    else:
        # Default action: update prices
        update_all_card_prices()
        get_price_update_summary()