import os
import requests
import json
from flask import Flask, render_template, request, redirect, url_for, flash, g
from datetime import date
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError # NEW: for handling duplicate collection names

load_dotenv()

# --- NEW HELPER FUNCTION ---
def get_exchange_rate(from_currency, to_currency):
    """
    Fetches the latest exchange rate from the Frankfurter API.
    Returns the rate as a float or None if an error occurs.
    """
    if from_currency == to_currency:
        return 1.0

    url = f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()
        rate = data['rates'].get(to_currency)
        if rate:
            return rate
        else:
            print(f"Error: Rate for {to_currency} not found in response.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching exchange rate: {e}")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing API response: {e}")
        return None
# --- END NEW HELPER FUNCTION ---

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev_secret_key'),
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.root_path, 'instance', 'one_piece_tcg.sqlite'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        EXCHANGE_RATE_API_KEY=os.getenv('EXCHANGE_RATE_API_KEY'),
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # MODIFIED: Import Collection model
    from .models import db, Card, WishlistItem, Collection
    db.init_app(app)

    with app.app_context():
        print(f"Creating database at: {app.config['SQLALCHEMY_DATABASE_URI']}")
        db.create_all()

    @app.route('/')
    def index():
        return render_template('index.html')

    # MODIFIED: Collection route to handle optional collection_id
    @app.route('/collection')
    @app.route('/collection/<int:collection_id>')
    def collection(collection_id=None):
        if collection_id:
            collection_obj = Collection.query.get_or_404(collection_id)
            cards = Card.query.filter_by(collection_id=collection_id).order_by(Card.name).all()
        else:
            # Default view for all cards not in a collection
            cards = Card.query.filter_by(collection_id=None).order_by(Card.name).all()
            collection_obj = None

        # NEW: Calculate the total purchase price in SGD
        total_purchase_price_sgd = sum(card.purchase_price_sgd * card.quantity for card in cards)

        card_names = sorted(list(set(card.name for card in cards)))
        card_values = {name: sum(c.purchase_price_sgd for c in cards if c.name == name) for name in card_names}

        # MODIFIED: Pass collections to the template for navigation
        all_collections = Collection.query.order_by(Collection.name).all()

        return render_template(
            'collection.html',
            cards=cards,
            collection=collection_obj,
            card_names=card_names,
            card_values=card_values,
            all_collections=all_collections,
            total_purchase_price_sgd=total_purchase_price_sgd # NEW: Pass the total to the template
        )

    # --- NEW COLLECTION ROUTES ---

    @app.route('/collections_list')
    def collections_list():
        collections = Collection.query.all()
        return render_template('collections_list.html', collections=collections)

    @app.route('/add_collection', methods=['GET', 'POST'])
    def add_collection():
        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            new_collection = Collection(name=name, description=description)
            try:
                db.session.add(new_collection)
                db.session.commit()
                flash('Collection created successfully!', 'success')
                return redirect(url_for('collections_list'))
            except IntegrityError:
                db.session.rollback()
                flash('Error: A collection with this name already exists.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {e}', 'danger')
                return redirect(url_for('add_collection'))
        return render_template('add_collection.html')

    @app.route('/edit_collection/<int:collection_id>', methods=['GET', 'POST'])
    def edit_collection(collection_id):
        collection = Collection.query.get_or_404(collection_id)
        if request.method == 'POST':
            collection.name = request.form['name']
            collection.description = request.form['description']
            try:
                db.session.commit()
                flash('Collection updated successfully!', 'success')
                return redirect(url_for('collections_list'))
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {e}', 'danger')
        return render_template('edit_collection.html', collection=collection)

    @app.route('/delete_collection/<int:collection_id>', methods=['POST'])
    def delete_collection(collection_id):
        collection = Collection.query.get_or_404(collection_id)
        try:
            # Permanently delete all cards associated with this collection
            for card in collection.cards:
                db.session.delete(card)
                
            db.session.delete(collection)
            db.session.commit()
            flash('Collection and all associated cards deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')
        return redirect(url_for('collections_list'))
    # --- END NEW COLLECTION ROUTES ---

    # --- MODIFIED `add_card` ROUTE ---
    @app.route('/add_card', methods=['GET', 'POST'])
    def add_card():
        if request.method == 'POST':
            name = request.form['name']
            set_name = request.form.get('set_name')
            card_number = request.form.get('card_number')
            rarity = request.form.get('rarity')
            color = request.form.get('color')
            quantity = int(request.form['quantity'])
            
            purchase_price_original = float(request.form['purchase_price_original'])
            original_currency = request.form.get('original_currency')
            current_value_sgd = float(request.form.get('current_value_sgd') or 0.0)
            image_url = request.form.get('image_url')
            purchase_date_str = request.form['purchase_date']
            
            # NEW: Get the selected collection ID from the form
            collection_id = request.form.get('collection_id')
            if collection_id == '': collection_id = None # Handle empty selection

            try:
                purchase_date = date.fromisoformat(purchase_date_str)
            except ValueError:
                flash('Invalid date format for purchase date.', 'error')
                return redirect(url_for('add_card', today_date=date.today().isoformat()))

            if original_currency and original_currency != 'SGD':
                rate = get_exchange_rate(original_currency, 'SGD')
                if rate:
                    purchase_price_sgd = purchase_price_original * rate
                    flash(f"Converted {purchase_price_original} {original_currency} to {purchase_price_sgd:.2f} SGD.", "info")
                else:
                    purchase_price_sgd = 0.0
                    flash("Failed to get exchange rate, purchase price in SGD set to 0.0", "warning")
            else:
                purchase_price_sgd = purchase_price_original

            new_card = Card(
                name=name, set_name=set_name, card_number=card_number, rarity=rarity,
                color=color, quantity=quantity, 
                purchase_price_original=purchase_price_original,
                original_currency=original_currency,
                purchase_price_sgd=purchase_price_sgd,
                current_value_sgd=current_value_sgd, image_url=image_url, 
                purchase_date=purchase_date,
                collection_id=collection_id # NEW: Pass the collection_id
            )
            try:
                db.session.add(new_card)
                db.session.commit()
                flash('Card added successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred while adding the card: {e}', 'danger')
            
            return redirect(url_for('collection'))

        # NEW: Query collections for the form dropdown
        collections = Collection.query.order_by(Collection.name).all()
        today_date = date.today().isoformat()
        return render_template('add_card.html', today_date=today_date, collections=collections)
    # --- END OF MODIFIED `add_card` ROUTE ---

    # --- MODIFIED `add_card_with_ai` ROUTE ---
    @app.route('/add_card_with_ai', methods=['GET', 'POST'])
    def add_card_with_ai():
        from .chatbot_service import get_card_details_from_ai_multimodal, generate_ai_confirmation_message
        
        if request.method == 'POST':
            user_description = request.form.get('card_description')
            card_image = request.files.get('card_image')
            
            # NEW: Get the selected collection ID
            collection_id = request.form.get('collection_id')
            if collection_id == '': collection_id = None

            if not user_description and (not card_image or card_image.filename == ''):
                flash("Please provide a card description or upload an image.", "error")
                return redirect(url_for('add_card_with_ai'))

            image_path = None
            if card_image and card_image.filename != '':
                try:
                    upload_folder = os.path.join(app.instance_path, 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    image_path = os.path.join(upload_folder, card_image.filename)
                    card_image.save(image_path)
                except Exception as e:
                    flash(f"Error saving image: {e}", "error")
                    return redirect(url_for('add_card_with_ai'))

            card_data = get_card_details_from_ai_multimodal(user_description, image_path)
            
            if image_path and os.path.exists(image_path):
                os.remove(image_path)

            if 'error' in card_data:
                flash(f"Error from AI: {card_data['error']}", "error")
                return redirect(url_for('add_card_with_ai'))

            try:
                purchase_price_original = card_data.get('purchase_price_original')
                original_currency = card_data.get('original_currency')

                if original_currency and original_currency != 'SGD':
                    rate = get_exchange_rate(original_currency, 'SGD')
                    if rate:
                        purchase_price_sgd = purchase_price_original * rate
                        flash(f"Converted {purchase_price_original} {original_currency} to {purchase_price_sgd:.2f} SGD.", "info")
                    else:
                        purchase_price_sgd = 0.0
                        flash("Failed to get exchange rate, purchase price in SGD set to 0.0", "warning")
                else:
                    purchase_price_sgd = purchase_price_original

                new_card = Card(
                    name=card_data.get('name'), set_name=card_data.get('set_name'),
                    card_number=card_data.get('card_number'), rarity=card_data.get('rarity'),
                    color=card_data.get('color'), quantity=int(card_data.get('quantity', 1)),
                    purchase_price_original=purchase_price_original,
                    original_currency=original_currency,
                    purchase_price_sgd=purchase_price_sgd,
                    current_value_sgd=float(card_data.get('current_value_sgd', 0.0)),
                    image_url=card_data.get('image_url'),
                    purchase_date=date.fromisoformat(card_data.get('purchase_date')),
                    collection_id=collection_id # NEW: Pass the collection_id
                )
                db.session.add(new_card)
                db.session.commit()
                
                confirmation_message = generate_ai_confirmation_message(card_data)
                flash(confirmation_message, 'success')
                
                return redirect(url_for('collection'))

            except Exception as e:
                db.session.rollback()
                flash(f"An error occurred while saving the card: {e}", "error")
                return redirect(url_for('add_card_with_ai'))
        
        # NEW: Query collections for the form dropdown
        collections = Collection.query.order_by(Collection.name).all()
        return render_template('add_card_with_ai.html', collections=collections)
    # --- END OF MODIFIED `add_card_with_ai` ROUTE ---

    @app.route('/edit_card/<int:card_id>', methods=['GET', 'POST'])
    def edit_card(card_id):
        card = db.session.get(Card, card_id)
        if not card:
            flash('Card not found!', 'error')
            return redirect(url_for('collection'))
        
        if request.method == 'POST':
            card.name = request.form['name']
            card.set_name = request.form.get('set_name')
            card.card_number = request.form.get('card_number')
            card.rarity = request.form.get('rarity')
            card.color = request.form.get('color')
            card.quantity = int(request.form['quantity'])

            card.purchase_price_original = float(request.form['purchase_price_original'])
            card.original_currency = request.form.get('original_currency')
            
            # NEW: Update the card's collection
            collection_id = request.form.get('collection_id')
            card.collection_id = int(collection_id) if collection_id else None

            # Perform currency conversion on edit
            if card.original_currency and card.original_currency != 'SGD':
                rate = get_exchange_rate(card.original_currency, 'SGD')
                if rate:
                    card.purchase_price_sgd = card.purchase_price_original * rate
                    flash(f"Converted {card.purchase_price_original} {card.original_currency} to {card.purchase_price_sgd:.2f} SGD.", "info")
                else:
                    card.purchase_price_sgd = 0.0
                    flash("Failed to get exchange rate, purchase price in SGD set to 0.0", "warning")
            else:
                card.purchase_price_sgd = card.purchase_price_original
            # --- END OF MODIFIED EDIT ROUTE ---

            card.current_value_sgd = float(request.form.get('current_value_sgd') or 0.0)
            card.image_url = request.form.get('image_url')
            
            purchase_date_str = request.form['purchase_date']
            try:
                card.purchase_date = date.fromisoformat(purchase_date_str)
            except ValueError:
                flash('Invalid date format for purchase date.', 'error')
                return redirect(url_for('edit_card', card_id=card.id))

            db.session.commit()
            flash('Card updated successfully!', 'success')
            return redirect(url_for('collection', collection_id=card.collection_id))
        
        # NEW: Query collections for the form dropdown
        collections = Collection.query.order_by(Collection.name).all()
        return render_template('edit_card.html', card=card, collections=collections)

    @app.route('/delete_card/<int:card_id>', methods=['POST'])
    def delete_card(card_id):
        card = db.session.get(Card, card_id)
        if not card:
            flash('Card not found!', 'error')
            return redirect(url_for('collection'))
        db.session.delete(card)
        db.session.commit()
        flash('Card deleted successfully!', 'success')
        return redirect(url_for('collection'))

    @app.route('/expenses')
    def expenses():
        all_expenses = Expense.query.order_by(Expense.expense_date.desc()).all()
        expense_categories = {}
        for expense in all_expenses:
            expense_categories[expense.category] = expense_categories.get(expense.category, 0) + expense.amount_sgd
        chart_labels = list(expense_categories.keys())
        chart_data = list(expense_categories.values())
        return render_template('expenses.html', expenses=all_expenses, chart_labels=chart_labels, chart_data=chart_data)

    @app.route('/add_expense', methods=['GET', 'POST'])
    def add_expense():
        all_cards = Card.query.order_by(Card.name).all()
        if request.method == 'POST':
            description = request.form['description']
            amount_sgd = float(request.form['amount_sgd'])
            category = request.form['category']
            expense_date_str = request.form['expense_date']
            card_id = request.form.get('card_id')
            try:
                expense_date = date.fromisoformat(expense_date_str)
            except ValueError:
                flash('Invalid date format for expense date.', 'error')
                return redirect(url_for('add_expense', today_date=date.today().isoformat(), cards=all_cards))
            linked_card_id = int(card_id) if card_id else None
            new_expense = Expense(
                description=description, amount_sgd=amount_sgd, category=category,
                expense_date=expense_date, card_id=linked_card_id
            )
            db.session.add(new_expense)
            db.session.commit()
            flash('Expense added successfully!', 'success')
            return redirect(url_for('expenses'))
        today_date = date.today().isoformat()
        return render_template('add_expense.html', today_date=today_date, cards=all_cards)
    
    @app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
    def edit_expense(expense_id):
        expense = db.session.get(Expense, expense_id)
        if not expense:
            flash('Expense not found!', 'error')
            return redirect(url_for('expenses'))
        all_cards = Card.query.order_by(Card.name).all()
        if request.method == 'POST':
            expense.description = request.form['description']
            expense.amount_sgd = float(request.form['amount_sgd'])
            expense.category = request.form['category']
            expense_date_str = request.form['expense_date']
            try:
                expense.expense_date = date.fromisoformat(expense_date_str)
            except ValueError:
                flash('Invalid date format for expense date.', 'error')
                return redirect(url_for('edit_expense', expense_id=expense.id))
            card_id = request.form.get('card_id')
            expense.card_id = int(card_id) if card_id else None
            db.session.commit()
            flash('Expense updated successfully!', 'success')
            return redirect(url_for('expenses'))
        return render_template('edit_expense.html', expense=expense, cards=all_cards)

    @app.route('/delete_expense/<int:expense_id>', methods=['POST'])
    def delete_expense(expense_id):
        expense = db.session.get(Expense, expense_id)
        if not expense:
            flash('Expense not found!', 'error')
            return redirect(url_for('expenses'))
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted successfully!', 'success')
        return redirect(url_for('expenses'))

    @app.route('/wishlist')
    def wishlist():
        wishlist_items = WishlistItem.query.order_by(WishlistItem.priority.desc(), WishlistItem.card_name).all()
        return render_template('wishlist.html', wishlist_items=wishlist_items)

    @app.route('/add_wishlist_item', methods=['POST'])
    def add_wishlist_item():
        card_name = request.form['card_name']
        set_name = request.form.get('set_name')
        target_price_sgd = float(request.form.get('target_price_sgd') or 0.0)
        priority = request.form.get('priority', 'Medium')
        new_wishlist_item = WishlistItem(
            card_name=card_name, set_name=set_name, target_price_sgd=target_price_sgd, priority=priority
        )
        db.session.add(new_wishlist_item)
        db.session.commit()
        flash('Wishlist item added successfully!', 'success')
        return redirect(url_for('wishlist'))
    
    @app.route('/edit_wishlist_item/<int:item_id>', methods=['GET', 'POST'])
    def edit_wishlist_item(item_id):
        item = db.session.get(WishlistItem, item_id)
        if not item:
            flash('Wishlist item not found!', 'error')
            return redirect(url_for('wishlist'))
        if request.method == 'POST':
            item.card_name = request.form['card_name']
            item.set_name = request.form.get('set_name')
            item.target_price_sgd = float(request.form.get('target_price_sgd') or 0.0)
            item.priority = request.form.get('priority', 'Medium')
            db.session.commit()
            flash('Wishlist item updated successfully!', 'success')
            return redirect(url_for('wishlist'))
        return render_template('edit_wishlist_item.html', item=item)

    @app.route('/delete_wishlist_item/<int:item_id>', methods=['POST'])
    def delete_wishlist_item(item_id):
        item = db.session.get(WishlistItem, item_id)
        if not item:
            flash('Wishlist item not found!', 'error')
            return redirect(url_for('wishlist'))
        db.session.delete(item)
        db.session.commit()
        flash('Wishlist item deleted successfully!', 'success')
        return redirect(url_for('wishlist'))

    @app.context_processor
    def inject_today_date():
        return {'today_date': date.today().isoformat()}

    @app.before_request
    def before_request():
        g.messages = []
    
    return app