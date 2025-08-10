print("Importing collections blueprint")
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Collection, Card

collections_bp = Blueprint('collections', __name__, template_folder='../templates')

@collections_bp.route('/')
def collections_list():
    collections = Collection.query.order_by(Collection.name).all()
    return render_template('collections_list.html', collections=collections)

@collections_bp.route('/add', methods=['GET', 'POST'])
def add_collection():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        new_collection = Collection(name=name, description=description)
        try:
            db.session.add(new_collection)
            db.session.commit()
            flash('Collection created successfully!', 'success')
            return redirect(url_for('collections.collections_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')
    return render_template('add_collection.html')

@collections_bp.route('/edit/<int:collection_id>', methods=['GET', 'POST'])
def edit_collection(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    if request.method == 'POST':
        collection.name = request.form['name']
        collection.description = request.form.get('description', '')
        try:
            db.session.commit()
            flash('Collection updated!', 'success')
            return redirect(url_for('collections.collections_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')
    return render_template('edit_collection.html', collection=collection)

@collections_bp.route('/delete/<int:collection_id>', methods=['POST'])
def delete_collection(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    try:
        for card in collection.cards:
            db.session.delete(card)
        db.session.delete(collection)
        db.session.commit()
        flash('Collection and cards deleted!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('collections.collections_list'))

@collections_bp.route('/view/<int:collection_id>')
def view_collection(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    cards = Card.query.filter_by(collection_id=collection_id).order_by(Card.name).all()
    total_price_sgd = sum(card.purchase_price_sgd * card.quantity for card in cards)
    return render_template('collection.html', collection=collection, cards=cards, total_price_sgd=total_price_sgd)
