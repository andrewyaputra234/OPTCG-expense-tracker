# One Piece TCG Expense Tracker

## Project Overview

This is a Flask-based web application designed to help One Piece Card Game players track and manage their card collections and associated expenses. It provides a simple, intuitive interface to organize your inventory, monitor card values, and generate sales messages.

## Key Features

* **Card Management:** Easily add, edit, and delete cards from your collection.
* **AI-Powered Card Lookup:** Use AI to automatically fetch card details (name, set, card number, rarity) from **one or more images** or text input.
* **Collection Organization:** Group your cards into custom collections (e.g., "Trade Binder," "Personal Deck," or a specific "Sale" lot).
* **Multi-Currency Support:** Track original purchase prices in their native currency (e.g., JPY, USD) and view the converted value in SGD.
* **Live Price Tracking:** Dynamically fetch and display live market prices for your cards.
* **Sales Tracking:** Automatically calculates total sales based on your cards' purchase prices and allows for optional additions like a mailing fee.
* **Intuitive Interface:** A clean, responsive user interface with a dedicated sidebar for easy navigation.

## Installation and Setup

Follow these steps to get the application up and running on your local machine.

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd one-piece-tcg-tracker
2. Set Up a Virtual Environment
It's recommended to use a virtual environment to manage project dependencies.

Bash

python -m venv venv
Activate the virtual environment:

On Windows:

Bash

venv\Scripts\activate
On macOS/Linux:

Bash

source venv/bin/activate
3. Install Dependencies
Install all the required Python libraries using the requirements.txt file, then install Playwright browsers (for live pricing scraping).

Bash

pip install -r requirements.txt
python -m playwright install chromium
4. Set Up Environment Variables
You will need to set a few environment variables for the application to run.

On Windows (PowerShell):

PowerShell

$env:FLASK_APP = "app.py"
$env:OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
On macOS/Linux:

Bash

export FLASK_APP=app.py
export OPENAI_API_KEY=YOUR_OPENAI_API_KEY
Replace YOUR_OPENAI_API_KEY with your actual API key.

5. Run the Application
Start the Flask development server (the project uses an app factory).

Bash

flask --app app:create_app run
The application will be available at http://127.0.0.1:5000.

How to Use
Once the application is running, you can:

Navigate to "My Collection" to view and manage your cards.

Add a new card manually or use the "Add Card (AI)" feature to auto-populate card details from an image.

Create new collections to sort your cards.

Input the original purchase price in its currency, and the app will calculate the equivalent SGD value.

On the "My Collection" page, you can enter any custom divisor to convert the total original price (e.g., in JPY) to your desired value in SGD. This allows for flexible currency conversion.

The total SGD value is calculated automatically for your entire collection, with an option to add a mailing fee.

Credits
This project was built with the help of a conversational AI assistant.
