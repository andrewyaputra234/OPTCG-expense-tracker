# fast_chatbot_service.py
"""
Optimized wrapper around the original chatbot_service.get_yuyutei_prices_by_card_number
Uses a persistent browser instance for much faster bulk operations while keeping 100% the same logic
"""

from playwright.sync_api import sync_playwright
import re

class FastYuyuteiPricer:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
    
    def __enter__(self):
        """Start the persistent browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the browser"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def get_yuyutei_prices_by_card_number_fast(self, card_number_raw, category=None):
        """
        EXACT SAME LOGIC as chatbot_service.get_yuyutei_prices_by_card_number
        but uses the persistent browser instead of creating a new one each time.
        
        This is a direct copy of your original function with only the browser part changed.
        """
        try:
            if '-' not in card_number_raw:
                card_number_formatted = f"{card_number_raw[:4]}-{card_number_raw[4:]}"
            else:
                card_number_formatted = card_number_raw
                
            url = f"https://yuyu-tei.jp/sell/opc/s/search?search_word={card_number_formatted}"
            
            # USE PERSISTENT BROWSER INSTEAD OF CREATING NEW ONE
            page = self.page
            page.goto(url, wait_until='networkidle')

            CARD_ITEM_SELECTOR = ".card-product"
            
            # Find all card products on the page that match the card number
            matching_cards = page.locator(f"{CARD_ITEM_SELECTOR}").all()
            
            if not matching_cards:
                print(f"Card '{card_number_formatted}' not found on Yuyu-tei search page.")
                return None

            results = []
            for card_element in matching_cards:
                # Get all text content from the card element to analyze
                full_text = card_element.text_content()
                
                # Check if this card matches our card number
                if card_number_formatted not in full_text:
                    continue

                # Extract different parts of the card information
                # Try multiple selectors to get the most complete information
                name_element = card_element.locator("span.d-block.border, .card-name, h3, .product-name").first
                price_element = card_element.locator("strong, .price, .sell-price").first
                rarity_element = card_element.locator("span.tag, .rarity, .card-rarity").first
                
                # Get the card name/title (which should include variant info)
                if name_element.count() > 0:
                    name_text = name_element.text_content().strip()
                else:
                    # Fallback: try to extract from full text
                    lines = full_text.split('\n')
                    name_text = next((line.strip() for line in lines if card_number_formatted in line), "Unknown Name")
                
                # Get price
                price_text = price_element.text_content().strip() if price_element.count() > 0 else "0"
                
                # Get rarity/condition info
                rarity_text = rarity_element.text_content().strip() if rarity_element.count() > 0 else "Normal"
                
                # Check for variant labels that appear on Yuyu-tei cards (like P-SR, SP, SR, etc.)
                full_text_lower = full_text.lower()
                variant_keywords = []
                
                # Look for specific Yuyu-tei variant labels
                if 'p-sr' in full_text_lower or 'psr' in full_text_lower:
                    variant_keywords.extend(['Parallel', 'SR'])
                elif 'p-r' in full_text_lower or 'pr' in full_text_lower:
                    variant_keywords.extend(['Parallel', 'R'])
                elif 'p-c' in full_text_lower or 'pc' in full_text_lower:
                    variant_keywords.extend(['Parallel', 'C'])
                elif 'sp' in full_text_lower and 'sp card' in full_text_lower:
                    variant_keywords.append('SP')
                elif 'sr card' in full_text_lower or (rarity_text.lower() in ['sr', 'super rare']):
                    variant_keywords.append('SR')
                elif 'sec card' in full_text_lower or 'secret' in full_text_lower:
                    variant_keywords.append('SEC')
                elif 'l card' in full_text_lower or 'leader card' in full_text_lower:
                    variant_keywords.append('Leader')
                
                # Additional checks for other variant indicators (can be combined with above)
                # Check for Manga illustrations (independent of other variants)
                if 'manga' in full_text_lower or 'illustration' in full_text_lower or 'マンガ' in full_text_lower:
                    variant_keywords.append('Manga')
                
                # Fallback checks for other variant indicators
                if not variant_keywords:
                    if 'parallel' in full_text_lower or 'パラレル' in full_text_lower:
                        variant_keywords.append('Parallel')
                    if 'special' in full_text_lower:
                        variant_keywords.append('SP')
                    if 'alternate art' in full_text_lower or 'aa' in full_text_lower:
                        variant_keywords.append('AA')
                
                # Remove duplicates while preserving order
                variant_keywords = list(dict.fromkeys(variant_keywords))
                
                # Enhance name with variant info if found
                if variant_keywords:
                    enhanced_name = f"{name_text} ({'/'.join(variant_keywords)})"
                else:
                    enhanced_name = name_text

                # Extract the price (digits only)
                price_match = re.search(r'(\d{1,3}(?:,\d{3})*)', price_text)
                price = int(price_match.group(1).replace(',', '')) if price_match else None
                
                # Category filtering based on variant keywords and full text
                card_matches_category = True
                if category:
                    category_lower = category.lower()
                    full_text_lower = full_text.lower()
                    enhanced_name_lower = enhanced_name.lower()
                    
                    # Category mapping for filtering based on Yuyu-tei variant labels
                    if category_lower == 'sp':
                        # SP includes both SP cards and Parallel variants (P-SR, P-R, P-C)
                        card_matches_category = ('SP' in variant_keywords or 
                                               'Parallel' in variant_keywords or
                                               'sp card' in full_text_lower or
                                               any('p-' in full_text_lower for _ in ['p-sr', 'p-r', 'p-c']))
                    elif category_lower == 'aa ldr':
                        card_matches_category = (('AA' in variant_keywords or 'alternate art' in full_text_lower) and 
                                               ('Leader' in variant_keywords or 'leader' in full_text_lower))
                    elif category_lower == 'aa':
                        card_matches_category = (('AA' in variant_keywords or 'alternate art' in full_text_lower) and 
                                               not ('Leader' in variant_keywords or 'leader' in full_text_lower))
                    elif category_lower == 'sec':
                        card_matches_category = ('SEC' in variant_keywords or 
                                               'sec card' in full_text_lower or 
                                               'secret' in full_text_lower)
                    elif category_lower == 'sr':
                        # Regular SR cards (not parallel)
                        card_matches_category = ('SR' in variant_keywords and 'Parallel' not in variant_keywords) or \
                                               ('sr card' in full_text_lower and 'p-sr' not in full_text_lower)
                    elif category_lower in ['mangas', 'event mangas']:
                        card_matches_category = ('Manga' in variant_keywords or 
                                               'illustration' in full_text_lower)
                    elif category_lower == 'regular':
                        # Regular cards - no special variants
                        card_matches_category = (len(variant_keywords) == 0 or 
                                               (len(variant_keywords) == 1 and variant_keywords[0] in ['R', 'C', 'UC']))
                
                if card_matches_category:
                    results.append({
                        'name': enhanced_name,
                        'original_name': name_text,
                        'card_number': card_number_formatted,
                        'rarity': rarity_text,
                        'price_yen': price,
                        'variant_keywords': variant_keywords,
                        'category_match': category if category else 'any',
                        'full_text_sample': full_text[:200] + "..." if len(full_text) > 200 else full_text
                    })
            
            if not results:
                print(f"No prices found for {card_number_formatted} after filtering.")
                return None
            
            return results

        except Exception as e:
            print(f"Error fetching Yuyu-tei prices for '{card_number_formatted}': {e}")
            return None