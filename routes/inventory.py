print("Importing inventory blueprint")
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, InventoryCard, PriceHistory
from chatbot_service import get_yuyutei_prices_by_card_number
from datetime import date, datetime, timedelta
import re

inventory_bp = Blueprint('inventory', __name__, template_folder='../templates')

# Exchange rate (you might want to fetch this dynamically)
JPY_TO_SGD_RATE = 0.009

@inventory_bp.route('/')
def inventory_list():
    """Display all inventory cards with current values and trends"""
    cards = InventoryCard.query.order_by(InventoryCard.name).all()
    
    # Calculate totals
    total_purchase_value_sgd = sum(card.purchase_price_sgd * card.quantity for card in cards)
    total_current_value_sgd = sum(card.current_price_sgd * card.quantity for card in cards)
    total_gain_loss = total_current_value_sgd - total_purchase_value_sgd
    total_gain_loss_percentage = (total_gain_loss / total_purchase_value_sgd * 100) if total_purchase_value_sgd > 0 else 0
    
    return render_template('inventory_list.html', 
                         cards=cards,
                         total_purchase_value=total_purchase_value_sgd,
                         total_current_value=total_current_value_sgd,
                         total_gain_loss=total_gain_loss,
                         total_gain_loss_percentage=total_gain_loss_percentage)

@inventory_bp.route('/add', methods=['GET', 'POST'])
def add_inventory_card():
    """Add a new card to inventory"""
    if request.method == 'POST':
        card_number = request.form['card_number'].strip()
        quantity = int(request.form.get('quantity', 1))
        purchase_price_yen = float(request.form.get('purchase_price_yen', 0))
        purchase_price_sgd = float(request.form.get('purchase_price_sgd', 0))
        condition = request.form.get('condition', 'Near Mint')
        notes = request.form.get('notes', '')
        
        try:
            # Fetch current market price from Yuyu-tei
            price_data = get_yuyutei_prices_by_card_number(card_number)
            
            if price_data and len(price_data) > 0:
                # Use the first result (you might want to let user choose if multiple)
                card_info = price_data[0]
                current_price_yen = card_info.get('price_yen', 0)
                current_price_sgd = current_price_yen * JPY_TO_SGD_RATE
                
                # Create inventory card
                new_card = InventoryCard(
                    name=card_info.get('name', 'Unknown'),
                    card_number=card_number,
                    rarity=card_info.get('rarity', 'Unknown'),
                    quantity=quantity,
                    purchase_price_yen=purchase_price_yen,
                    purchase_price_sgd=purchase_price_sgd,
                    current_price_yen=current_price_yen,
                    current_price_sgd=current_price_sgd,
                    condition=condition,
                    notes=notes,
                    last_price_update=datetime.utcnow()
                )
                
                db.session.add(new_card)
                db.session.flush()  # Get the ID
                
                # Create initial price history entry
                price_entry = PriceHistory(
                    inventory_card_id=new_card.id,
                    price_yen=current_price_yen,
                    price_sgd=current_price_sgd,
                    jpy_to_sgd_rate=JPY_TO_SGD_RATE
                )
                
                db.session.add(price_entry)
                db.session.commit()
                
                flash(f'Card {card_number} added to inventory successfully!', 'success')
                return redirect(url_for('inventory.inventory_list'))
            else:
                flash(f'Could not fetch price data for card {card_number}. Please try again.', 'error')
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding card: {str(e)}', 'error')
    
    return render_template('add_inventory_card.html')

@inventory_bp.route('/card/<int:card_id>')
def view_card_details(card_id):
    """View detailed information about a specific inventory card including price history"""
    card = InventoryCard.query.get_or_404(card_id)
    
    # Get price history for the last 30 days
    thirty_days_ago = date.today() - timedelta(days=30)
    price_history = PriceHistory.query.filter(
        PriceHistory.inventory_card_id == card_id,
        PriceHistory.date_recorded >= thirty_days_ago
    ).order_by(PriceHistory.date_recorded.desc()).all()
    
    # Calculate statistics
    if len(price_history) > 1:
        latest_price = price_history[0].price_sgd
        oldest_price = price_history[-1].price_sgd
        price_change = latest_price - oldest_price
        price_change_percentage = (price_change / oldest_price * 100) if oldest_price > 0 else 0
        
        # Find highest and lowest prices in the period
        all_prices = [p.price_sgd for p in price_history]
        highest_price = max(all_prices)
        lowest_price = min(all_prices)
    else:
        price_change = 0
        price_change_percentage = 0
        highest_price = card.current_price_sgd
        lowest_price = card.current_price_sgd
    
    return render_template('inventory_card_details.html', 
                         card=card, 
                         price_history=price_history,
                         price_change=price_change,
                         price_change_percentage=price_change_percentage,
                         highest_price=highest_price,
                         lowest_price=lowest_price)

@inventory_bp.route('/update_prices', methods=['POST'])
def update_all_prices():
    """Update prices for all inventory cards"""
    cards = InventoryCard.query.all()
    updated_count = 0
    
    for card in cards:
        try:
            price_data = get_yuyutei_prices_by_card_number(card.card_number)
            
            if price_data and len(price_data) > 0:
                current_price_yen = price_data[0].get('price_yen', 0)
                current_price_sgd = current_price_yen * JPY_TO_SGD_RATE
                
                # Update card's current price
                card.current_price_yen = current_price_yen
                card.current_price_sgd = current_price_sgd
                card.last_price_update = datetime.utcnow()
                
                # Add to price history (only if it's a different day or significantly different price)
                latest_history = PriceHistory.query.filter_by(
                    inventory_card_id=card.id,
                    date_recorded=date.today()
                ).first()
                
                if not latest_history:
                    # No entry for today, create one
                    price_entry = PriceHistory(
                        inventory_card_id=card.id,
                        price_yen=current_price_yen,
                        price_sgd=current_price_sgd,
                        jpy_to_sgd_rate=JPY_TO_SGD_RATE
                    )
                    db.session.add(price_entry)
                else:
                    # Update today's entry
                    latest_history.price_yen = current_price_yen
                    latest_history.price_sgd = current_price_sgd
                
                updated_count += 1
                
        except Exception as e:
            print(f"Error updating price for card {card.card_number}: {e}")
            continue
    
    try:
        db.session.commit()
        flash(f'Successfully updated prices for {updated_count} cards!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating prices: {str(e)}', 'error')
    
    return redirect(url_for('inventory.inventory_list'))

@inventory_bp.route('/card/<int:card_id>/price_data')
def get_card_price_data(card_id):
    """API endpoint to get price history data for charts"""
    card = InventoryCard.query.get_or_404(card_id)
    
    # Get price history for the last 30 days
    thirty_days_ago = date.today() - timedelta(days=30)
    price_history = PriceHistory.query.filter(
        PriceHistory.inventory_card_id == card_id,
        PriceHistory.date_recorded >= thirty_days_ago
    ).order_by(PriceHistory.date_recorded.asc()).all()
    
    # Format data for chart
    dates = [p.date_recorded.strftime('%Y-%m-%d') for p in price_history]
    prices_sgd = [p.price_sgd for p in price_history]
    prices_yen = [p.price_yen for p in price_history]
    
    return jsonify({
        'dates': dates,
        'prices_sgd': prices_sgd,
        'prices_yen': prices_yen,
        'card_name': card.name,
        'card_number': card.card_number
    })

@inventory_bp.route('/card/<int:card_id>/edit', methods=['GET', 'POST'])
def edit_inventory_card(card_id):
    """Edit inventory card details"""
    card = InventoryCard.query.get_or_404(card_id)
    
    if request.method == 'POST':
        card.quantity = int(request.form.get('quantity', card.quantity))
        card.purchase_price_yen = float(request.form.get('purchase_price_yen', card.purchase_price_yen))
        card.purchase_price_sgd = float(request.form.get('purchase_price_sgd', card.purchase_price_sgd))
        card.condition = request.form.get('condition', card.condition)
        card.notes = request.form.get('notes', card.notes)
        
        try:
            db.session.commit()
            flash('Card updated successfully!', 'success')
            return redirect(url_for('inventory.view_card_details', card_id=card_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating card: {str(e)}', 'error')
    
    return render_template('edit_inventory_card.html', card=card)

@inventory_bp.route('/card/<int:card_id>/delete', methods=['POST'])
def delete_inventory_card(card_id):
    """Delete a card from inventory"""
    card = InventoryCard.query.get_or_404(card_id)
    
    try:
        # Price history will be deleted automatically due to cascade
        db.session.delete(card)
        db.session.commit()
        flash('Card deleted from inventory!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting card: {str(e)}', 'error')
    
    return redirect(url_for('inventory.inventory_list'))

@inventory_bp.route('/analytics')
def analytics():
    """Show inventory analytics and trends"""
    cards = InventoryCard.query.all()
    
    # Calculate various metrics
    total_cards = sum(card.quantity for card in cards)
    total_purchase_value = sum(card.purchase_price_sgd * card.quantity for card in cards)
    total_current_value = sum(card.current_price_sgd * card.quantity for card in cards)
    
    # Top gainers and losers
    card_performances = []
    for card in cards:
        if card.purchase_price_sgd > 0:
            gain_loss = (card.current_price_sgd - card.purchase_price_sgd) * card.quantity
            gain_loss_percentage = (card.current_price_sgd - card.purchase_price_sgd) / card.purchase_price_sgd * 100
            card_performances.append({
                'card': card,
                'gain_loss': gain_loss,
                'gain_loss_percentage': gain_loss_percentage
            })
    
    # Sort by percentage gain/loss
    card_performances.sort(key=lambda x: x['gain_loss_percentage'], reverse=True)
    top_gainers = card_performances[:5]
    top_losers = card_performances[-5:]
    
    return render_template('inventory_analytics.html',
                         total_cards=total_cards,
                         total_purchase_value=total_purchase_value,
                         total_current_value=total_current_value,
                         top_gainers=top_gainers,
                         top_losers=top_losers)