import os
from flask import Flask, render_template, request, redirect, url_for, flash, g
from datetime import date
from dotenv import load_dotenv

load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev_secret_key'),
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.instance_path, 'one_piece_tcg.sqlite'),
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

    from .models import db, Card, Expense, WishlistItem
    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/collection')
    def collection():
        cards = Card.query.order_by(Card.name).all()
        card_names = [card.name for card in cards]
        card_values = [card.current_value_sgd if card.current_value_sgd is not None else 0 for card in cards]

        return render_template(
            'collection.html',
            cards=cards,
            card_names=card_names,
            card_values=card_values
        )

    @app.route('/add_card', methods=['GET', 'POST'])
    def add_card():
        if request.method == 'POST':
            name = request.form['name']
            set_name = request.form.get('set_name')
            card_number = request.form.get('card_number')
            rarity = request.form.get('rarity')
            color = request.form.get('color')
            quantity = int(request.form['quantity'])
            purchase_price_sgd = float(request.form['purchase_price_sgd'])
            current_value_sgd = float(request.form.get('current_value_sgd') or 0.0)
            image_url = request.form.get('image_url')
            purchase_date_str = request.form['purchase_date']

            try:
                purchase_date = date.fromisoformat(purchase_date_str)
            except ValueError:
                flash('Invalid date format for purchase date.', 'error')
                return redirect(url_for('add_card', today_date=date.today().isoformat()))

            new_card = Card(
                name=name, set_name=set_name, card_number=card_number, rarity=rarity,
                color=color, quantity=quantity, purchase_price_sgd=purchase_price_sgd,
                current_value_sgd=current_value_sgd, image_url=image_url, purchase_date=purchase_date
            )
            db.session.add(new_card)
            db.session.commit()

            flash('Card added successfully!', 'success')
            return redirect(url_for('collection'))

        today_date = date.today().isoformat()
        return render_template('add_card.html', today_date=today_date)

    @app.route('/add_card_with_ai', methods=['GET', 'POST'])
    def add_card_with_ai():
        from .chatbot_service import get_card_details_from_ai
        
        if request.method == 'POST':
            user_description = request.form.get('card_description')
            if not user_description:
                flash("Please provide a card description.", "error")
                return redirect(url_for('add_card_with_ai'))

            card_data = get_card_details_from_ai(user_description)
            
            if 'error' in card_data:
                flash(f"Error from AI: {card_data['error']}", "error")
                return redirect(url_for('add_card_with_ai'))

            try:
                new_card = Card(
                    name=card_data.get('name'), set_name=card_data.get('set_name'),
                    card_number=card_data.get('card_number'), rarity=card_data.get('rarity'),
                    color=card_data.get('color'), quantity=int(card_data.get('quantity', 1)),
                    purchase_price_sgd=float(card_data.get('purchase_price_sgd', 0.0)),
                    current_value_sgd=float(card_data.get('current_value_sgd', 0.0)),
                    image_url=card_data.get('image_url'),
                    purchase_date=date.fromisoformat(card_data.get('purchase_date'))
                )
                db.session.add(new_card)
                db.session.commit()
                
                flash('Card added successfully with AI!', 'success')
                return redirect(url_for('collection'))

            except Exception as e:
                db.session.rollback()
                flash(f"An error occurred while saving the card: {e}", "error")
                return redirect(url_for('add_card_with_ai'))

        return render_template('add_card_with_ai.html')

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
            card.purchase_price_sgd = float(request.form['purchase_price_sgd'])
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
            return redirect(url_for('collection'))
        
        return render_template('edit_card.html', card=card)

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