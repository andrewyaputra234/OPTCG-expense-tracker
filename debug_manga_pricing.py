"""
Test script to debug Manga card pricing issues
Run this to test Manga card price fetching with detailed debugging
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from chatbot_service import get_yuyutei_prices_by_card_number

def test_manga_card_pricing(card_number):
    """Test Manga card pricing with detailed output"""
    print(f"\n🔍 TESTING MANGA CARD PRICING FOR: {card_number}")
    print("=" * 50)
    
    try:
        # Fetch all price variants
        price_data = get_yuyutei_prices_by_card_number(card_number)
        
        if not price_data:
            print("❌ No price data found on Yuyu-tei")
            return
        
        print(f"📦 Found {len(price_data)} total variants on Yuyu-tei:")
        
        # Show all variants found
        for i, variant in enumerate(price_data):
            price = variant.get('price_yen', 0)
            name = variant.get('name', 'Unknown')
            keywords = variant.get('variant_keywords', [])
            print(f"  #{i+1}: ¥{price:,} - {name}")
            if keywords:
                print(f"      Keywords: {', '.join(keywords)}")
        
        # Apply Manga pricing logic
        print(f"\n📚 MANGA PRICING LOGIC:")
        
        # Extended price range for Manga cards
        valid_prices = [p for p in price_data if 50 <= p.get('price_yen', 0) <= 1000000]
        print(f"  Valid prices (¥50 - ¥1,000,000): {len(valid_prices)}")
        
        if valid_prices:
            # Sort by price (highest first)
            sorted_prices = sorted(valid_prices, key=lambda x: x.get('price_yen', 0), reverse=True)
            
            print(f"\n  📊 Valid options ranked by price:")
            for i, option in enumerate(sorted_prices):
                price = option.get('price_yen', 0)
                name = option.get('name', 'Unknown')
                print(f"    #{i+1}: ¥{price:,} - {name}")
            
            # Select highest price
            selected = max(valid_prices, key=lambda x: x.get('price_yen', 0))
            selected_price = selected.get('price_yen', 0)
            selected_name = selected.get('name', 'Unknown')
            
            print(f"\n  ✅ HIGHEST PRICE SELECTED:")
            print(f"     Price: ¥{selected_price:,}")
            print(f"     Name: {selected_name}")
            print(f"     SGD Equivalent: S${selected_price * 0.0086:.2f}")
        else:
            print("  ❌ No valid prices found within range")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    # Test with common Manga card numbers
    test_cards = [
        "OP02-013",  # Common Manga card
        "OP01-001",  # Another potential Manga
        "OP03-001"   # Another test case
    ]
    
    for card_num in test_cards:
        test_manga_card_pricing(card_num)