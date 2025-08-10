from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Card, Collection
from datetime import date
import requests

cards_bp = Blueprint('cards', __name__, template_folder='../templates')

def get_exchange_rate(from_currency, to_currency='SGD'):
    if from_currency == to_currency:
        return 1.0
    url = f"https://api.frankfurter.app/latest?from={from_currency}&to={to_currency}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        rate = data['rates'].get(to_currency)
        return rate or None
    except Exception as e:
        print(f"Exchange rate error: {e}")
        return None

@cards_bp.route('/')
def list_cards():
    cards = Card.query.order_by(Card.name).all()
    return render_template('cards.html', cards=cards)

@cards_bp.route('/add', methods=['GET', 'POST'])
def add_card():
    collections = Collection.query.order_by(Collection.name).all()
    if request.method == 'POST':
        name = request.form['name']
        set_name = request.form.get('set_name')
        card_number = request.form.get('card_number')
        rarity = request.form.get('rarity')
        color = request.form.get('color')
        quantity = int(request.form['quantity'])
        purchase_price_original = float(request.form['purchase_price_original'])
        original_currency = request.form.get('original_currency', 'SGD')
        current_value_sgd = float(request.form.get('current_value_sgd') or 0.0)
        image_url = request.form.get('image_url')
        purchase_date_str = request.form['purchase_date']
        collection_id = request.form.get('collection_id')
        if collection_id == '':
            collection_id = None
        try:
            purchase_date = date.fromisoformat(purchase_date_str)
        except ValueError:
            flash('Invalid purchase date format', 'danger')
            return redirect(url_for('cards.add_card'))
        if original_currency != 'SGD':
            rate = get_exchange_rate(original_currency, 'SGD')
            if rate:
                purchase_price_sgd = purchase_price_original * rate
            else:
                purchase_price_sgd = 0.0
                flash('Failed to get exchange rate, setting price SGD to 0', 'warning')
        else:
            purchase_price_sgd = purchase_price_original

        new_card = Card(
            name=name,
            set_name=set_name,
            card_number=card_number,
            rarity=rarity,
            color=color,
            quantity=quantity,
            purchase_price_original=purchase_price_original,
            original_currency=original_currency,
            purchase_price_sgd=purchase_price_sgd,
            current_value_sgd=current_value_sgd,
            image_url=image_url,
            purchase_date=purchase_date,
            collection_id=collection_id
        )
        try:
            db.session.add(new_card)
            db.session.commit()
            flash('Card added successfully!', 'success')
            return redirect(url_for('cards.list_cards'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding card: {e}', 'danger')
    return render_template('add_card.html', collections=collections, today_date=date.today().isoformat())

@cards_bp.route('/edit/<int:card_id>', methods=['GET', 'POST'])
def edit_card(card_id):
    card = Card.query.get_or_404(card_id)
    collections = Collection.query.order_by(Collection.name).all()
    if request.method == 'POST':
        card.name = request.form['name']
        card.set_name = request.form.get('set_name')
        card.card_number = request.form.get('card_number')
        card.rarity = request.form.get('rarity')
        card.color = request.form.get('color')
        card.quantity = int(request.form['quantity'])
        card.purchase_price_original = float(request.form['purchase_price_original'])
        card.original_currency = request.form.get('original_currency', 'SGD')
        collection_id = request.form.get('collection_id')
        card.collection_id = int(collection_id) if collection_id else None

        if card.original_currency != 'SGD':
            rate = get_exchange_rate(card.original_currency, 'SGD')
            if rate:
                card.purchase_price_sgd = card.purchase_price_original * rate
            else:
                card.purchase_price_sgd = 0.0
                flash('Failed to get exchange rate, setting price SGD to 0', 'warning')
        else:
            card.purchase_price_sgd = card.purchase_price_original

        card.current_value_sgd = float(request.form.get('current_value_sgd') or 0.0)
        card.image_url = request.form.get('image_url')
        try:
            card.purchase_date = date.fromisoformat(request.form['purchase_date'])
        except ValueError:
            flash('Invalid purchase date format', 'danger')
            return redirect(url_for('cards.edit_card', card_id=card.id))

        try:
            db.session.commit()
            flash('Card updated!', 'success')
            return redirect(url_for('cards.list_cards'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating card: {e}', 'danger')

    return render_template('edit_card.html', card=card, collections=collections)

@cards_bp.route('/delete/<int:card_id>', methods=['POST'])
def delete_card(card_id):
    card = Card.query.get_or_404(card_id)
    try:
        db.session.delete(card)
        db.session.commit()
        flash('Card deleted!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting card: {e}', 'danger')
    return redirect(url_for('cards.list_cards'))
