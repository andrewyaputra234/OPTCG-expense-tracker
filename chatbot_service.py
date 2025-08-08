# chatbot_service.py
import os
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv
import json
from datetime import date
import base64

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Your original text-only function
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

# --- START OF NEW MULTIMODAL FUNCTION ---
def get_card_details_from_ai_multimodal(user_description: str = None, image_path: str = None) -> dict:
    if not user_description and not image_path:
        return {"error": "No description or image provided."}

    system_prompt = (
        "You are an expert at extracting One Piece Card Game (OPTCG) details from images and text. "
        "Your goal is to provide a JSON object with the following fields: 'name', 'set_name', "
        "'card_number', 'rarity', 'color', 'quantity', 'purchase_price_sgd', 'purchase_date' "
        "(YYYY-MM-DD), and 'image_url'. If an image is provided, prioritize information from the image. "
        "If a field is not available, use sensible defaults (e.g., quantity: 1, price: 0.0, "
        "date: today's date, empty string for others). "
        "For 'rarity', identify common rarities like SR, R, UC, C, or special versions like Parallel, "
        "Manga Art, or Alt-Art (AA). "
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
        print(f"AI Raw Response: {ai_response_content}")

        # Handle cases where the AI returns None or an empty response
        if ai_response_content is None:
            return {"error": "AI response content was empty. The AI may not have been able to process the request."}
        
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
        card_data.setdefault('current_value_sgd', 0.0)

        return card_data

    except OpenAIError as e:
        return {"error": f"OpenAI API Error: {e.args[0]}"}
    
    except json.JSONDecodeError:
        return {"error": "AI response was not in a valid JSON format."}
    
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}
# --- END OF NEW MULTIMODAL FUNCTION ---

def generate_ai_confirmation_message(card_data: dict) -> str:
    """Generates a friendly confirmation message from the card data."""
    system_prompt = (
        "You are a helpful assistant that generates friendly, one-sentence confirmation "
        "messages for a user who has just added a trading card to their collection. "
        "Acknowledge the card and its key details. Do not include prices or dates. "
        "Example: 'Got it! I've added a Parallel Art Luffy from the OP05 set to your collection.' "
        "Your output should be a single, concise sentence."
    )
    user_message = f"Generate a confirmation message for the following card details: {json.dumps(card_data)}"

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
    description = "I got 2 copies of Zoro from OP01, a Super Rare for $25 each."
    details = get_card_details_from_ai(description)
    print(f"Details from text: {details}")

    # You can test with a local image file path here
    # details_with_image = get_card_details_from_ai_multimodal(image_path="path/to/your/image.jpg")
    # print(f"Details from image: {details_with_image}")