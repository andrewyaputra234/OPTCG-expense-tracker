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
This project has the following key files and directories:

.
├── app.py                  # The main Flask application file with all routes
├── models.py               # Defines the database models (Card, Collection, Expense, etc.)
├── one_piece_tcg.sqlite    # The SQLite database file (created automatically)
├── requirements.txt        # Project dependencies
├── templates/
│   ├── base.html           # The base template with navigation
│   ├── index.html          # Homepage
│   ├── collection.html     # Main card collection page with sidebar
│   ├── collections_list.html # Page for managing collections
│   ├── add_collection.html # Form for adding a new collection
│   ├── edit_collection.html  # Form for editing a collection
│   ├── add_card.html       # Form for adding a card
│   ├── add_card_with_ai.html # AI-powered card addition form
│   └── edit_card.html      # Form for editing an existing card
└── README.md

```bash