# chatbot_service.py
import os
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv
import json
from datetime import date

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_card_details_from_ai(user_description: str) -> dict:
    if not user_description or not user_description.strip():
        return {"error": "No description provided."}

    if len(user_description) > 500:
        return {"error": "Input description is too long. Please be more concise."}

    system_prompt = (
        "You are a helpful assistant that extracts One Piece Card Game (OPTCG) card details "
        "from user descriptions. Your goal is to provide a JSON object with the following fields: "
        "'name', 'set_name', 'card_number', 'rarity', 'color', 'quantity', 'purchase_price_sgd', "
        "'purchase_date' (YYYY-MM-DD), and 'image_url'. "
        "If a field is not explicitly mentioned or inferable from the description, use sensible defaults "
        "(e.g., quantity: 1, purchase_date: today's date, price: 0.0, empty string for others). "
        "For 'card_number', try to infer the set (e.g., 'OP01', 'ST10'). "
        "If a type like 'SP', 'AA' (Alternative Art), or 'Manga Art' is mentioned, include it in the 'rarity' field "
        "or infer the 'card_number' if possible (e.g. Manga Art often have specific card numbers). "
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
        card_data = json.loads(ai_response_content)
        
        card_data.setdefault('name', 'Unknown Card')
        card_data.setdefault('set_name', '')
        card_data.setdefault('card_number', '')
        card_data.setdefault('rarity', '')
        card_data.setdefault('color', '')
        card_data.setdefault('quantity', 1)
        card_data.setdefault('purchase_price_sgd', 0.0)
        card_data.setdefault('purchase_date', date.today().isoformat())
        card_data.setdefault('image_url', '')

        return card_data

    except OpenAIError as e:
        return {"error": f"OpenAI API Error: {e.args[0]}"}
    
    except json.JSONDecodeError:
        return {"error": "AI response was not in a valid format."}
    
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

if __name__ == "__main__":
    description = "I got 2 copies of Zoro from OP01, a Super Rare for $25 each."
    details = get_card_details_from_ai(description)
    print(f"Details: {details}")