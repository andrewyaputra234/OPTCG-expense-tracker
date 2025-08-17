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

# --- ADDED HELPER FUNCTION FROM app.py ---
def get_yuyutei_prices_by_card_number(card_number_raw):
    """
    Fetch all available prices for a card number from Yuyu-tei's search page.
    
    Args:
        card_number_raw (str): e.g. 'OP01-025' or 'OP01-121'
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
            
            matching_cards = page.locator(f"{CARD_ITEM_SELECTOR}").all()
            
            if not matching_cards:
                print(f"Card '{card_number_formatted}' not found on Yuyu-tei search page.")
                browser.close()
                return None

            results = []
            for card_element in matching_cards:
                name_and_number_element = card_element.locator("span.d-block.border")
                price_element = card_element.locator("strong")
                rarity_element = card_element.locator("span.tag")
                
                if card_number_formatted not in name_and_number_element.text_content():
                    continue

                name_text = name_and_number_element.text_content().strip() if name_and_number_element.count() > 0 else "Unknown Name"
                price_text = price_element.text_content().strip() if price_element.count() > 0 else "0"
                rarity_text = rarity_element.text_content().strip() if rarity_element.count() > 0 else "Normal"

                price_match = re.search(r'(\d{1,3}(?:,\d{3})*)', price_text)
                price = int(price_match.group(1).replace(',', '')) if price_match else None
                
                results.append({
                    'name': name_text,
                    'card_number': card_number_formatted,
                    'rarity': rarity_text,
                    'price_yen': price
                })
            
            browser.close()
            
            if not results:
                print(f"No prices found for {card_number_formatted} after filtering.")
                return None
            
            return results

    except Exception as e:
        print(f"Error fetching Yuyu-tei prices for '{card_number_formatted}': {e}")
        return None
# --- END ADDED HELPER FUNCTION ---

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
            
            for card in card_list:
                # --- NEW LOGIC: Override the quantity to 1 for each image ---
                card['quantity'] = 1
                # --- END NEW LOGIC ---

                set_name = card.get('set_name', '')
                card_number = card.get('card_number', '')

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

            return card_list

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

        if set_name:
            if 'Parallel' in rarity or 'Alt-Art' in rarity:
                 confirmation_messages.append(f"Successfully added a {rarity} {card_name} from the {set_name} set to your collection.")
            else:
                confirmation_messages.append(f"Successfully added a {card_name} from the {set_name} set to your collection.")
        else:
            confirmation_messages.append(f"Successfully added a {card_name} to your collection.")

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