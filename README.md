# One Piece Card Game (OPTCG) Expense Tracker

## Project Overview

This is a Flask-based web application designed to help One Piece Card Game players track their card collection, expenses, and wishlists. The application provides a simple interface to manage your card inventory, organize cards into custom collections, and monitor their value.

## Key Features

* **Card Management:** Easily add, edit, and delete cards from your collection.
* **AI-Powered Card Lookup:** Use AI to automatically fetch card details like name, set, card number, and rarity from an image or text input.
* **Multi-Currency Support:** Track the original purchase price of a card in its native currency (e.g., JPY, USD) and see its converted value in SGD.
* **Collection Management:** Organize your cards into custom collections, such as "Trade Binder," "Personal Deck," or specific "Sale" lots.
* **Intuitive Interface:** A clean, responsive user interface with a dedicated sidebar for navigating between collections.
* **Wishlist Tracking:** Maintain a list of cards you want to acquire with target prices and priority levels.
* **Expense Logging:** Track all expenses related to your card collection.

## Installation and Setup

Follow these steps to get the application up and running on your local machine.

### 1. Clone the Repository

git clone <your-repository-url>
cd OPTCG expense tracker

### 2. Set Up a Virtual Environment
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
### 3. Install Dependencies
Install all the required Python libraries.

Bash

pip install -r requirements.txt
(Note: If you don't have a requirements.txt file, you can create one by running pip freeze > requirements.txt after installing your libraries like Flask, Flask-SQLAlchemy, etc.)

### 4. Set Up Environment Variables
You will need to set a few environment variables for the application to run.

On Windows (PowerShell):

PowerShell

$env:FLASK_APP = "app.py"
$env:GOOGLE_API_KEY = "YOUR_GOOGLE_GENERATIVE_AI_API_KEY"
On macOS/Linux:

Bash

export FLASK_APP=app.py
export GOOGLE_API_KEY=YOUR_GOOGLE_GENERATIVE_AI_API_KEY
Replace YOUR_GOOGLE_GENERATIVE_AI_API_KEY with your actual API key.

### 5. Run the Application
Start the Flask development server.

Bash

flask run
The application will be available at http://127.0.0.1:5000.

File Structure
