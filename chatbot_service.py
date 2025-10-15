# chatbot_service.py
import os
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv
import json
from datetime import date
import base64
from typing import Dict, Any, List
import re
# --- NEW IMPORTS FOR LIVE PRICING ---
from playwright.sync_api import sync_playwright
# --- END NEW IMPORTS ---

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- UPDATED HELPER FUNCTION FOR LIVE PRICING ---
def get_yuyutei_prices_by_card_number(card_number_raw, category=None):
    """
    Fetch all available prices for a card number from Yuyu-tei's search page.
    
    Args:
        card_number_raw (str): e.g. 'OP01-025' or 'OP01-121'
        category (str, optional): Filter by category like 'SP', 'AA', 'SEC', 'Mangas', etc.
    Returns:
        List[Dict] or None: A list of dictionaries with card details and prices.
    """
    try:
        if '-' not in card_number_raw:
            card_number_formatted = f"{card_number_raw[:4]}-{card_number_raw[4:]}"
        else:
            card_number_formatted = card_number_raw
            
        url = f"https://yuyu-tei.jp/sell/opc/s/search?search_word={card_number_formatted}"
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, wait_until='networkidle')

            CARD_ITEM_SELECTOR = ".card-product"
            
            # Find all card products on the page that match the card number
            matching_cards = page.locator(f"{CARD_ITEM_SELECTOR}").all()
            
            if not matching_cards:
                print(f"Card '{card_number_formatted}' not found on Yuyu-tei search page.")
                browser.close()
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
                    elif category_lower == 'mangas':
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
            
            browser.close()
            
            if not results:
                print(f"No prices found for {card_number_formatted} after filtering.")
                return None
            
            return results

    except Exception as e:
        print(f"Error fetching Yuyu-tei prices for '{card_number_formatted}': {e}")
        return None
# --- END UPDATED HELPER FUNCTION ---

# Your function for text-only input (unchanged, still returns a single card)
def get_card_details_from_ai(user_description: str) -> Dict[str, Any]:
    if not user_description or not user_description.strip():
        return {"error": "No description provided."}

    if len(user_description) > 500:
        return {"error": "Input description is too long. Please be more concise."}

    system_prompt = (
        "You are a helpful assistant that extracts One Piece Card Game (OPTCG) card details "
        "from user descriptions. Your goal is to provide a single JSON object with the following fields: "
        "'name', 'set_name', 'card_number', 'rarity', 'color', 'quantity', "
        "'purchase_price_original', 'original_currency', "
        "'purchase_date' (YYYY-MM-DD), and 'image_url'. "
        "For 'original_currency', identify the currency symbol (e.g., '¥', '$', 'SGD') and use its 3-letter code (e.g., 'JPY', 'USD', 'SGD'). If no currency is specified, assume it's 'SGD'. "
        "If a field is not explicitly mentioned, use sensible defaults (e.g., quantity: 1, price: 0.0, date: today's date, empty string for others). "
        "Ensure the output is valid JSON only."
    )

    user_message = f"Please extract card details from this description: '{user_description}'"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"}
        )
        
        ai_response_content = response.choices[0].message.content
        ai_card_data = json.loads(ai_response_content)
        
        set_name = ai_card_data.get('set_name', '')
        card_number = ai_card_data.get('card_number', '')

        full_card_number = f"{set_name}-{card_number}" if set_name and card_number else card_number

        card_data = {
            'name': ai_card_data.get('name', 'Unknown Card'),
            'set_name': set_name,
            'card_number': full_card_number,
            'rarity': ai_card_data.get('rarity', ''),
            'color': ai_card_data.get('color', ''),
            'quantity': ai_card_data.get('quantity', 1),
            'purchase_price_original': ai_card_data.get('purchase_price_original', 0.0),
            'original_currency': ai_card_data.get('original_currency', 'SGD'),
            'purchase_date': date.today().isoformat(),
            'image_url': ai_card_data.get('image_url', ''),
        }

        return card_data

    except OpenAIError as e:
        return {"error": f"OpenAI API Error: {e.args[0]}"}
    
    except json.JSONDecodeError:
        return {"error": "AI response was not in a valid JSON format."}
    
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

# --- MODIFIED: Multimodal function now handles multiple cards and adds live pricing ---
def get_card_details_from_ai_multimodal(user_description: str = None, image_paths: List[str] = None) -> List[Dict[str, Any]]:
    # MODIFIED: Check for empty description AND empty image list
    if not user_description and not image_paths:
        return {"error": "No description or image provided."}

    system_prompt = (
        "You are an expert at extracting One Piece Card Game (OPTCG) details from images and text. "
        "Your goal is to provide a **JSON list of objects**, one for each card. "
        "If an image is provided, prioritize information from the image. "
        "Each object must contain the following fields: 'name', 'set_name', "
        "'card_number', 'rarity', 'color', 'quantity', "
        "'purchase_price_original', 'original_currency', "
        "'purchase_date' (YYYY-MM-DD), and 'image_url'. "
        "For 'original_currency', identify the currency symbol (e.g., '¥', '$', 'SGD') and use its 3-letter code (e.g., 'JPY', 'USD', 'SGD'). If no currency is specified, assume it's 'SGD'. "
        "If a field is not available, use sensible defaults (e.g., quantity: 1, price: 0.0, date: today's date, empty string for others). "
        "For 'rarity', identify common rarities like SR, R, UC, C, or special versions like Parallel, "
        "Manga Art, or Alt-Art (AA). "
        "If the user mentions or if the card text/image includes \"P/L\", \"PL\", or \"Parallel Leader\", set the rarity to \"Parallel/Leader\" regardless of other rarity descriptions. "
        "Ensure the output is valid JSON only, without any other text or explanation."
    )

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    content_list = []
    if user_description:
        content_list.append({"type": "text", "text": user_description})

    # NEW LOGIC: Loop through each image path and add it to the content list
    if image_paths:
        for image_path in image_paths:
            try:
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                content_list.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                })
            except Exception as e:
                return {"error": f"Error processing image file: {e}"}

    messages.append({"role": "user", "content": content_list})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=4000
        )
        
        ai_response_content = response.choices[0].message.content
        
        if ai_response_content is None:
            return {"error": "AI response content was empty. The AI may not have been able to process the request."}
        
        json_match = re.search(r'(\[.*?\]|\{.*?\})', ai_response_content, re.DOTALL)
        
        if json_match:
            json_string = json_match.group(1)
            raw_card_data = json.loads(json_string)

            if not isinstance(raw_card_data, list):
                card_list = [raw_card_data]
            else:
                card_list = raw_card_data
            
            # NEW LOGIC: This new dictionary will store unique cards
            final_card_map = {}
            for card in card_list:
                # Use a unique key for each card based on its key properties
                card_key = (card.get('name', ''), card.get('set_name', ''), card.get('card_number', ''))
                
                if card_key in final_card_map:
                    # If the card already exists, just add to the quantity
                    final_card_map[card_key]['quantity'] += card.get('quantity', 1)
                else:
                    # If it's a new card, add it to the map
                    final_card_map[card_key] = card
                    
            final_card_list = list(final_card_map.values())

            # Now, process the list for live prices and other formatting
            for card in final_card_list:
                set_name = card.get('set_name', '')
                card_number = card.get('card_number', '')
                
                 # --- ADD THIS NEW LINE RIGHT HERE ---
                card['purchase_date'] = date.today().isoformat()
                # ------------------------------------
                
                if set_name and card_number:
                    full_card_number = f"{set_name}-{card_number.replace(f'{set_name}-', '')}"
                    card['card_number'] = full_card_number
                else:
                    full_card_number = card_number
                
                if full_card_number:
                    prices = get_yuyutei_prices_by_card_number(full_card_number)
                    if prices:
                        card['live_price_jpy'] = prices[0]['price_yen']
                        print(f"Found live price for {full_card_number}: {card['live_price_jpy']} JPY")
                    else:
                        card['live_price_jpy'] = 0
                        print(f"No live price found for {full_card_number}")
                else:
                    card['live_price_jpy'] = 0
                        
            return final_card_list

        else:
            return {"error": "AI response did not contain a valid JSON list or object."}

    except OpenAIError as e:
        return {"error": f"OpenAI API Error: {e.args[0]}"}
    
    except json.JSONDecodeError as e:
        return {"error": f"AI response was not in a valid JSON format: {e}"}
    
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}


# --- MODIFIED: Function to handle a list of cards ---
def generate_ai_confirmation_message(card_data_list: List[Dict[str, Any]]) -> str:
    """Generates a friendly confirmation message for a list of cards."""
    if not isinstance(card_data_list, list) or not card_data_list:
        return "No card details to confirm."

    confirmation_messages = []
    
    for card_data in card_data_list:
        card_name = card_data.get('name', 'a card')
        set_name = card_data.get('set_name', '')
        rarity = card_data.get('rarity', 'Parallel Art')
        count = card_data.get('quantity', 1)

        if set_name:
            if 'Parallel' in rarity or 'Alt-Art' in rarity:
                 confirmation_messages.append(f"Successfully added {count} {rarity} {card_name} from the {set_name} set to your collection.")
            else:
                confirmation_messages.append(f"Successfully added {count} {card_name} from the {set_name} set to your collection.")
        else:
            confirmation_messages.append(f"Successfully added {count} {card_name} to your collection.")

    return " ".join(confirmation_messages)

if __name__ == "__main__":
    # Example usage for the single card function
    description = "I got a Zoro from OP01, a Super Rare for $25."
    details = get_card_details_from_ai(description)
    print(f"Details from text: {details}")

    # Example usage for the multi-card function
    multi_description = "I bought 2 Ace SP cards for 30 SGD each and a Zoro SP card for 20 SGD."
    multi_details = get_card_details_from_ai_multimodal(multi_description)
    print(f"\nDetails from multi-card description: {multi_details}")
    if not 'error' in multi_details:
        confirmation = generate_ai_confirmation_message(multi_details)
        print(f"Confirmation message: {confirmation}")