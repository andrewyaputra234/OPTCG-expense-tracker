# chatbot_service.py
import os
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv
import json
from datetime import date
import base64
from typing import Dict, Any

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Your function for text-only input
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
        
        card_data = {
            'name': ai_card_data.get('name', 'Unknown Card'),
            'set_name': ai_card_data.get('set_name', ''),
            'card_number': ai_card_data.get('card_number', ''),
            'rarity': ai_card_data.get('rarity', ''),
            'color': ai_card_data.get('color', ''),
            'quantity': ai_card_data.get('quantity', 1),
            'purchase_price_original': ai_card_data.get('purchase_price_original', 0.0),
            'original_currency': ai_card_data.get('original_currency', 'SGD'),
            'purchase_date': date.today().isoformat(), # Always use today's date
            'image_url': ai_card_data.get('image_url', ''),
        }

        return card_data

    except OpenAIError as e:
        return {"error": f"OpenAI API Error: {e.args[0]}"}
    
    except json.JSONDecodeError:
        return {"error": "AI response was not in a valid JSON format."}
    
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

# Your multimodal function for a single card
def get_card_details_from_ai_multimodal(user_description: str = None, image_path: str = None) -> Dict[str, Any]:
    if not user_description and not image_path:
        return {"error": "No description or image provided."}

    system_prompt = (
        "You are an expert at extracting One Piece Card Game (OPTCG) details from images and text. "
        "Your goal is to provide a single JSON object with the following fields: 'name', 'set_name', "
        "'card_number', 'rarity', 'color', 'quantity', "
        "'purchase_price_original', 'original_currency', "
        "'purchase_date' (YYYY-MM-DD), and 'image_url'. "
        "If an image is provided, prioritize information from the image. "
        "For 'original_currency', identify the currency symbol (e.g., '¥', '$', 'SGD') and use its 3-letter code (e.g., 'JPY', 'USD', 'SGD'). If no currency is specified, assume it's 'SGD'. "
        "If a field is not available, use sensible defaults (e.g., quantity: 1, price: 0.0, date: today's date, empty string for others). "
        "For 'rarity', identify common rarities like SR, R, UC, C, or special versions like Parallel, "
        "Manga Art, or Alt-Art (AA). "
        "If the user mentions or if the card text/image includes \"P/L\", \"PL\", or \"Parallel Leader\", set the rarity to \"Parallel/Leader\" regardless of other rarity descriptions. "
        "Ensure the output is valid JSON only."
    )

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    content_list = []
    if user_description:
        content_list.append({"type": "text", "text": f"Extract card details from this description: '{user_description}'"})
    if image_path:
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
            response_format={"type": "json_object"}
        )
        
        ai_response_content = response.choices[0].message.content
        
        if ai_response_content is None:
            return {"error": "AI response content was empty. The AI may not have been able to process the request."}
        
        ai_card_data = json.loads(ai_response_content)
        
        card_data = {
            'name': ai_card_data.get('name', 'Unknown Card'),
            'set_name': ai_card_data.get('set_name', ''),
            'card_number': ai_card_data.get('card_number', ''),
            'rarity': ai_card_data.get('rarity', ''),
            'color': ai_card_data.get('color', ''),
            'quantity': ai_card_data.get('quantity', 1),
            'purchase_price_original': ai_card_data.get('purchase_price_original', 0.0),
            'original_currency': ai_card_data.get('original_currency', 'SGD'),
            'purchase_date': date.today().isoformat(), # Always use today's date
            'image_url': ai_card_data.get('image_url', '')
        }
        
        if image_path and os.path.exists(image_path):
            os.remove(image_path)

        return card_data

    except OpenAIError as e:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        return {"error": f"OpenAI API Error: {e.args[0]}"}
    
    except json.JSONDecodeError:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        return {"error": "AI response was not in a valid JSON format."}
    
    except Exception as e:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        return {"error": f"An unexpected error occurred: {e}"}

def generate_ai_confirmation_message(card_data: dict) -> str:
    """Generates a friendly confirmation message from the card data."""
    system_prompt = (
        "You are a helpful assistant that generates friendly, one-sentence confirmation "
        "messages for a user who has just added a trading card to their collection. "
        "Acknowledge the card and its key details. Do not include prices or dates. "
        "Example: 'Got it! I've added a Parallel Art Luffy from the OP05 set to your collection.' "
        "Your output should be a single, concise sentence."
    )
    
    # Create a copy to safely modify the date without changing the original object
    data_for_ai = card_data.copy()
    
    # Convert date object to a string if it exists
    if 'purchase_date' in data_for_ai and isinstance(data_for_ai['purchase_date'], date):
        data_for_ai['purchase_date'] = data_for_ai['purchase_date'].isoformat()

    user_message = f"Generate a confirmation message for the following card details: {json.dumps(data_for_ai)}"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content
    except OpenAIError:
        return "Card added successfully with AI!"

if __name__ == "__main__":
    description = "I got a Zoro from OP01, a Super Rare for $25."
    details = get_card_details_from_ai(description)
    print(f"Details from text: {details}")