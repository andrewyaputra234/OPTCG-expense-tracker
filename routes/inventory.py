print("Importing inventory blueprint")
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, InventoryCard, PriceHistory
from chatbot_service import get_yuyutei_prices_by_card_number
from datetime import date, datetime, timedelta
import re
import os
from werkzeug.utils import secure_filename

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
        # Check if using AI (image upload) or manual entry
        use_ai = request.form.get('use_ai') == 'true'
        
        if use_ai:
            return _add_inventory_card_with_ai()
        else:
            return _add_inventory_card_manual()
    
    return render_template('add_inventory_card.html')

def _add_inventory_card_manual():
    """Manual card entry"""
    card_number = request.form['card_number'].strip()
    quantity = int(request.form.get('quantity', 1))
    purchase_price_yen = float(request.form.get('purchase_price_yen', 0))
    purchase_price_sgd = float(request.form.get('purchase_price_sgd', 0))
    condition = request.form.get('condition', 'Near Mint')
    notes = request.form.get('notes', '')
    
    try:
        # Fetch current market price from Yuyu-tei (YEN - PRIMARY)
        price_data = get_yuyutei_prices_by_card_number(card_number)
        
        if price_data and len(price_data) > 0:
            # Use the first result (you might want to let user choose if multiple)
            card_info = price_data[0]
            current_price_yen = card_info.get('price_yen', 0)
            
            # For purchase prices: Use what user entered
            # If user didn't enter Yen purchase price, use current market price as reference
            final_purchase_price_yen = purchase_price_yen if purchase_price_yen > 0 else current_price_yen
            final_purchase_price_sgd = purchase_price_sgd  # Always use what user entered for SGD
            
            # For current SGD: Only calculate if user didn't provide SGD purchase price
            calculated_current_sgd = current_price_yen * JPY_TO_SGD_RATE if final_purchase_price_sgd == 0 else final_purchase_price_sgd
            
            # Create inventory card with SEPARATE currency tracking
            new_card = InventoryCard(
                name=card_info.get('name', 'Unknown'),
                card_number=card_number,
                rarity=card_info.get('rarity', 'Unknown'),
                quantity=quantity,
                purchase_price_yen=final_purchase_price_yen,
                purchase_price_sgd=final_purchase_price_sgd,
                current_price_yen=current_price_yen,      # PRIMARY - from Yuyu-tei
                current_price_sgd=calculated_current_sgd,  # SECONDARY - manual or calculated
                condition=condition,
                notes=notes,
                primary_currency='YEN',  # Focus on Yen trends
                track_yen_trends=True,   # Always track Yen
                track_sgd_trends=(final_purchase_price_sgd > 0),  # Only track SGD if user provided it
                last_price_update_yen=datetime.utcnow(),
                last_price_update_sgd=datetime.utcnow() if final_purchase_price_sgd > 0 else None
            )
            
            db.session.add(new_card)
            db.session.flush()  # Get the ID
            
            # Create initial price history entry with SEPARATE tracking
            price_entry = PriceHistory(
                inventory_card_id=new_card.id,
                price_yen=current_price_yen,
                yen_source='yuyu-tei',
                yen_fetched_at=datetime.utcnow(),
                price_sgd=calculated_current_sgd if final_purchase_price_sgd > 0 else None,
                sgd_source='manual' if final_purchase_price_sgd > 0 else None,
                sgd_updated_at=datetime.utcnow() if final_purchase_price_sgd > 0 else None,
                jpy_to_sgd_rate=JPY_TO_SGD_RATE if final_purchase_price_sgd == 0 else None
            )
            
            db.session.add(price_entry)
            db.session.commit()
            
            flash(f'Card {card_number} added to inventory! Tracking: {"Yen (primary)" + (", SGD (manual)" if final_purchase_price_sgd > 0 else ", SGD (calculated)")}', 'success')
            return redirect(url_for('inventory.inventory_list'))
        else:
            flash(f'Could not fetch Yen price data for card {card_number}. Please try again.', 'error')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding card: {str(e)}', 'error')
    
    return render_template('add_inventory_card.html')

def _add_inventory_card_with_ai():
    """Add inventory card using AI image recognition"""
    from chatbot_service import get_card_details_from_ai_multimodal, generate_ai_confirmation_message
    from werkzeug.utils import secure_filename
    import os
    
    user_description = request.form.get('card_description', '')
    uploaded_files = request.files.getlist('card_image')
    quantity = int(request.form.get('quantity', 1))
    purchase_price_yen = float(request.form.get('purchase_price_yen', 0))
    purchase_price_sgd = float(request.form.get('purchase_price_sgd', 0))
    condition = request.form.get('condition', 'Near Mint')
    notes = request.form.get('notes', '')
    
    # Check if any files were uploaded
    if not user_description and not any(file.filename for file in uploaded_files):
        flash("Please provide a card description or upload at least one image.", "error")
        return render_template('add_inventory_card.html')
    
    image_paths = []
    
    try:
        # Save uploaded images
        for card_image in uploaded_files:
            if card_image and card_image.filename != '':
                from flask import current_app
                upload_folder = os.path.join(current_app.instance_path, 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                
                # Use a secure filename to prevent malicious uploads
                filename = secure_filename(card_image.filename)
                image_path = os.path.join(upload_folder, filename)
                
                # Check if a file with the same name already exists to prevent overwriting
                if os.path.exists(image_path):
                    # Append a unique identifier to the filename
                    name, ext = os.path.splitext(filename)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                    filename = f"{name}_{timestamp}{ext}"
                    image_path = os.path.join(upload_folder, filename)
                
                card_image.save(image_path)
                image_paths.append(image_path)
        
        # Get card details from AI
        card_data_list = get_card_details_from_ai_multimodal(user_description, image_paths)
        
        # Clean up the temporary image files
        for path in image_paths:
            if os.path.exists(path):
                os.remove(path)
        
        if isinstance(card_data_list, dict) and 'error' in card_data_list:
            flash(f"Error from AI: {card_data_list['error']}", "error")
            return render_template('add_inventory_card.html')
        
        if not isinstance(card_data_list, list) or not card_data_list:
            flash("The AI did not return a list of cards. Please try a different image or description.", "error")
            return render_template('add_inventory_card.html')
        
        # Process each card from AI response
        added_cards = []
        for card_data in card_data_list:
            card_number = card_data.get('card_number')
            if not card_number:
                continue
            
            # Fetch current market price
            price_data = get_yuyutei_prices_by_card_number(card_number)
            
            if price_data and len(price_data) > 0:
                current_price_yen = price_data[0].get('price_yen', 0)
                current_price_sgd = current_price_yen * JPY_TO_SGD_RATE
                
                # Use user-provided purchase prices if available, otherwise use AI data
                final_purchase_price_yen = purchase_price_yen if purchase_price_yen > 0 else card_data.get('live_price_jpy', 0)
                final_purchase_price_sgd = purchase_price_sgd if purchase_price_sgd > 0 else (final_purchase_price_yen * JPY_TO_SGD_RATE)
                
                # Create inventory card
                new_card = InventoryCard(
                    name=card_data.get('name', 'Unknown'),
                    set_name=card_data.get('set_name'),
                    card_number=card_number,
                    rarity=card_data.get('rarity', 'Unknown'),
                    color=card_data.get('color'),
                    quantity=quantity,
                    purchase_price_yen=final_purchase_price_yen,
                    purchase_price_sgd=final_purchase_price_sgd,
                    current_price_yen=current_price_yen,
                    current_price_sgd=current_price_sgd,
                    condition=condition,
                    notes=notes,
                    image_url=card_data.get('image_url'),
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
                added_cards.append(new_card)
        
        if added_cards:
            db.session.commit()
            confirmation_message = generate_ai_confirmation_message(card_data_list)
            flash(f'Successfully added {len(added_cards)} card(s) to inventory! {confirmation_message}', 'success')
            return redirect(url_for('inventory.inventory_list'))
        else:
            flash('No cards could be processed. Please check the images and try again.', 'error')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error processing cards: {str(e)}', 'error')
        # Clean up image files on error
        for path in image_paths:
            if os.path.exists(path):
                os.remove(path)
    
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
    """Update YEN prices for all inventory cards (primary focus)"""
    cards = InventoryCard.query.all()
    updated_count = 0
    
    for card in cards:
        try:
            # FOCUS: Only update YEN prices from Yuyu-tei (primary tracking)
            price_data = get_yuyutei_prices_by_card_number(card.card_number)
            
            if price_data and len(price_data) > 0:
                current_price_yen = price_data[0].get('price_yen', 0)
                
                # Update ONLY Yen price (don't touch SGD unless it was calculated)
                card.current_price_yen = current_price_yen
                card.last_price_update_yen = datetime.utcnow()
                
                # Only update SGD if it's calculated (not manual)
                if not card.track_sgd_trends or card.purchase_price_sgd == 0:
                    card.current_price_sgd = current_price_yen * JPY_TO_SGD_RATE
                    card.last_price_update_sgd = datetime.utcnow()
                
                # Add to price history with SEPARATE tracking
                latest_history = PriceHistory.query.filter_by(
                    inventory_card_id=card.id,
                    date_recorded=date.today()
                ).first()
                
                if not latest_history:
                    # No entry for today, create one focusing on YEN
                    price_entry = PriceHistory(
                        inventory_card_id=card.id,
                        price_yen=current_price_yen,
                        yen_source='yuyu-tei',
                        yen_fetched_at=datetime.utcnow(),
                        # Only add SGD if it's calculated, not manual
                        price_sgd=card.current_price_sgd if not card.track_sgd_trends or card.purchase_price_sgd == 0 else None,
                        sgd_source='calculated' if not card.track_sgd_trends or card.purchase_price_sgd == 0 else None,
                        sgd_updated_at=datetime.utcnow() if not card.track_sgd_trends or card.purchase_price_sgd == 0 else None,
                        jpy_to_sgd_rate=JPY_TO_SGD_RATE if not card.track_sgd_trends or card.purchase_price_sgd == 0 else None
                    )
                    db.session.add(price_entry)
                else:
                    # Update today's YEN entry (primary focus)
                    latest_history.price_yen = current_price_yen
                    latest_history.yen_fetched_at = datetime.utcnow()
                    
                    # Only update SGD if it's calculated
                    if not card.track_sgd_trends or card.purchase_price_sgd == 0:
                        latest_history.price_sgd = card.current_price_sgd
                        latest_history.sgd_updated_at = datetime.utcnow()
                        latest_history.jpy_to_sgd_rate = JPY_TO_SGD_RATE
                
                updated_count += 1
                
        except Exception as e:
            print(f"Error updating YEN price for card {card.card_number}: {e}")
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
    """API endpoint to get price history data for charts - FOCUS on YEN trends"""
    card = InventoryCard.query.get_or_404(card_id)
    
    # Get price history for the last 30 days
    thirty_days_ago = date.today() - timedelta(days=30)
    price_history = PriceHistory.query.filter(
        PriceHistory.inventory_card_id == card_id,
        PriceHistory.date_recorded >= thirty_days_ago,
        PriceHistory.price_yen.isnot(None)  # Only entries with Yen data
    ).order_by(PriceHistory.date_recorded.asc()).all()
    
    # Format data for chart - PRIMARY focus on YEN
    dates = [p.date_recorded.strftime('%Y-%m-%d') for p in price_history]
    prices_yen = [p.price_yen for p in price_history]
    
    # SGD data only if available and user wants it
    prices_sgd = []
    has_sgd_data = False
    
    if card.track_sgd_trends:
        prices_sgd = [p.price_sgd for p in price_history if p.price_sgd is not None]
        has_sgd_data = len(prices_sgd) > 0
    
    return jsonify({
        'dates': dates,
        'prices_yen': prices_yen,        # PRIMARY - always available
        'prices_sgd': prices_sgd if has_sgd_data else [],  # SECONDARY - optional
        'has_sgd_data': has_sgd_data,
        'primary_currency': card.primary_currency,
        'track_yen_trends': card.track_yen_trends,
        'track_sgd_trends': card.track_sgd_trends,
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
        
        # Handle current price updates
        new_current_price_yen = float(request.form.get('current_price_yen', card.current_price_yen))
        new_current_price_sgd = float(request.form.get('current_price_sgd', card.current_price_sgd))
        
        # Track if prices were manually updated
        yen_price_changed = new_current_price_yen != card.current_price_yen
        sgd_price_changed = new_current_price_sgd != card.current_price_sgd
        
        # Update current prices
        card.current_price_yen = new_current_price_yen
        card.current_price_sgd = new_current_price_sgd
        
        # Update timestamps for manually changed prices
        if yen_price_changed:
            card.last_price_update_yen = datetime.utcnow()
        if sgd_price_changed:
            card.last_price_update_sgd = datetime.utcnow()
            card.track_sgd_trends = True  # Enable SGD tracking if user manually sets price
        
        try:
            db.session.commit()
            
            # Create price history entry if prices changed
            if yen_price_changed or sgd_price_changed:
                # Check if we already have an entry for today
                today_entry = PriceHistory.query.filter_by(
                    inventory_card_id=card.id,
                    date_recorded=date.today()
                ).first()
                
                if today_entry:
                    # Update existing entry
                    if yen_price_changed:
                        today_entry.price_yen = new_current_price_yen
                        today_entry.yen_source = 'manual'
                        today_entry.yen_fetched_at = datetime.utcnow()
                    if sgd_price_changed:
                        today_entry.price_sgd = new_current_price_sgd
                        today_entry.sgd_source = 'manual'
                        today_entry.sgd_updated_at = datetime.utcnow()
                else:
                    # Create new entry
                    price_entry = PriceHistory(
                        inventory_card_id=card.id,
                        price_yen=card.current_price_yen,
                        yen_source='manual' if yen_price_changed else 'yuyu-tei',
                        yen_fetched_at=datetime.utcnow() if yen_price_changed else card.last_price_update_yen,
                        price_sgd=card.current_price_sgd,
                        sgd_source='manual' if sgd_price_changed else ('manual' if card.track_sgd_trends else 'calculated'),
                        sgd_updated_at=datetime.utcnow() if sgd_price_changed else card.last_price_update_sgd
                    )
                    db.session.add(price_entry)
                
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

@inventory_bp.route('/card/<int:card_id>/quick_price_update', methods=['POST'])
def quick_price_update(card_id):
    """Quick update of card price from inventory list"""
    card = InventoryCard.query.get_or_404(card_id)
    
    try:
        new_price_yen = float(request.form.get('new_price_yen', 0))
        
        if new_price_yen >= 0:
            # Update the card price
            card.current_price_yen = new_price_yen
            card.last_price_update_yen = datetime.utcnow()
            
            # Create or update price history
            today_entry = PriceHistory.query.filter_by(
                inventory_card_id=card.id,
                date_recorded=date.today()
            ).first()
            
            if today_entry:
                today_entry.price_yen = new_price_yen
                today_entry.yen_source = 'manual'
                today_entry.yen_fetched_at = datetime.utcnow()
            else:
                price_entry = PriceHistory(
                    inventory_card_id=card.id,
                    price_yen=new_price_yen,
                    yen_source='manual',
                    yen_fetched_at=datetime.utcnow(),
                    price_sgd=card.current_price_sgd,
                    sgd_source='manual' if card.track_sgd_trends else 'calculated',
                    sgd_updated_at=card.last_price_update_sgd
                )
                db.session.add(price_entry)
            
            db.session.commit()
            flash(f'Price updated for {card.name} to ¥{int(new_price_yen)}', 'success')
        else:
            flash('Invalid price entered', 'error')
            
    except (ValueError, TypeError):
        flash('Invalid price format', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating price: {str(e)}', 'error')
    
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