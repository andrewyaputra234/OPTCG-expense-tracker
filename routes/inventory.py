print("Importing inventory blueprint")
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, InventoryCard, PriceHistory
from chatbot_service import get_yuyutei_prices_by_card_number
from datetime import date, datetime, timedelta
import re

inventory_bp = Blueprint('inventory', __name__, template_folder='../templates')

# Exchange rate (updated to more current rate)
JPY_TO_SGD_RATE = 0.0086  # More accurate JPY to SGD rate as of 2024/2025

def detect_category_from_text(text):
    """Auto-detect category from user input text (case-insensitive)"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Priority order - check for specific keywords
    # Check for manga variants first (highest priority)
    if any(keyword in text_lower for keyword in ['manga', 'mangas']):
        return 'Mangas'
    
    # Check for SP variants
    if any(keyword in text_lower for keyword in ['sp', 'special']):
        return 'SP'
    
    # Check for AA LDR variants
    if any(keyword in text_lower for keyword in ['aa ldr', 'aa leader', 'alternative art leader', 'alt art leader', 'leader aa', 'ldr aa']):
        return 'AA LDR'
    
    # Check for SEC variants
    if any(keyword in text_lower for keyword in ['sec', 'secret', 'secret rare']):
        return 'SEC'
    
    # Check for AA variants (but not AA LDR)
    if any(keyword in text_lower for keyword in ['aa', 'alternative art', 'alt art']) and 'leader' not in text_lower and 'ldr' not in text_lower:
        return 'AA'
    
    # Check for SR variants
    if any(keyword in text_lower for keyword in ['sr', 'super rare']):
        return 'SR'
    
    return None

@inventory_bp.route('/')
def inventory_list():
    """Display all inventory cards with current values and trends"""
    # Get category filter and sorting from query parameters
    selected_category = request.args.get('category', 'All')
    sort_by = request.args.get('sort_by', 'current_price')  # Default to current price
    sort_order = request.args.get('sort_order', 'desc')  # Default to highest first
    
    # Build base query
    query = InventoryCard.query
    
    # Filter cards based on selected category
    if selected_category != 'All':
        query = query.filter_by(category=selected_category)
    
    # Apply sorting
    if sort_by == 'name':
        if sort_order == 'desc':
            query = query.order_by(InventoryCard.name.desc())
        else:
            query = query.order_by(InventoryCard.name.asc())
    elif sort_by == 'purchase_price':
        if sort_order == 'desc':
            query = query.order_by(InventoryCard.purchase_price_yen.desc())
        else:
            query = query.order_by(InventoryCard.purchase_price_yen.asc())
    elif sort_by == 'current_price':
        if sort_order == 'desc':
            query = query.order_by(InventoryCard.current_price_yen.desc())
        else:
            query = query.order_by(InventoryCard.current_price_yen.asc())
    elif sort_by == 'total_value':
        # For total value, we'll sort by current_price_yen * quantity
        # We'll sort in Python since SQLAlchemy might not handle complex expressions well
        pass  # Handle this after query execution
    elif sort_by == 'pnl':
        # For P&L, we'll sort by (current_price_yen - purchase_price_yen) * quantity  
        # We'll sort in Python since SQLAlchemy might not handle complex expressions well
        pass  # Handle this after query execution
    elif sort_by == 'last_updated':
        if sort_order == 'desc':
            query = query.order_by(InventoryCard.last_price_update.desc().nullslast())
        else:
            query = query.order_by(InventoryCard.last_price_update.asc().nullslast())
    else:
        # Default sorting by name
        query = query.order_by(InventoryCard.name.asc())
    
    cards = query.all()
    
    # Handle sorting for calculated fields (total_value and pnl)
    if sort_by == 'total_value':
        cards.sort(key=lambda card: card.current_price_yen * card.quantity, reverse=(sort_order == 'desc'))
    elif sort_by == 'pnl':
        cards.sort(key=lambda card: (card.current_price_yen - card.purchase_price_yen) * card.quantity, reverse=(sort_order == 'desc'))
    
    # Get all available categories for dropdown (ordered by priority/value: highest to lowest)
    all_categories = ['All', 'Mangas', 'SP', 'AA LDR', 'AA', 'SEC', 'SR', 'Regular']
    
    # Calculate totals in JPY (for filtered cards)
    total_purchase_value_yen = sum(card.purchase_price_yen * card.quantity for card in cards)
    total_current_value_yen = sum(card.current_price_yen * card.quantity for card in cards)
    total_gain_loss_yen = total_current_value_yen - total_purchase_value_yen
    total_gain_loss_percentage = (total_gain_loss_yen / total_purchase_value_yen * 100) if total_purchase_value_yen > 0 else 0
    
    # Get category counts for better overview
    all_cards = InventoryCard.query.all()
    category_counts = {}
    for category in ['Mangas', 'SP', 'AA LDR', 'AA', 'SEC', 'SR', 'Regular']:
        count = len([card for card in all_cards if card.category == category])
        if count > 0:
            category_counts[category] = count
    
    return render_template('inventory_list.html', 
                         cards=cards,
                         selected_category=selected_category,
                         all_categories=all_categories,
                         category_counts=category_counts,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         total_purchase_value_yen=total_purchase_value_yen,
                         total_current_value_yen=total_current_value_yen,
                         total_gain_loss_yen=total_gain_loss_yen,
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
        category = request.form.get('category', 'Regular')
        notes = request.form.get('notes', '')
        
        try:
            # Fetch current market price from Yuyu-tei (get all variants)
            price_data = get_yuyutei_prices_by_card_number(card_number)
            
            if price_data and len(price_data) > 0:
                # Filter for reasonable prices (between ¥50 and ¥50000)
                valid_prices = [p for p in price_data if 50 <= p.get('price_yen', 0) <= 50000]
                
                if valid_prices:
                    # Priority order for highest price selection:
                    # 1. Mangas (ALWAYS highest price - top priority)
                    # 2. SP (second highest value)
                    # 3. Others use first result
                    if category == 'Mangas':
                        # Manga cards ALWAYS get the absolute highest price
                        card_info = max(valid_prices, key=lambda x: x.get('price_yen', 0))
                        print(f"Manga card detected - using HIGHEST price: ¥{card_info.get('price_yen', 0):,}")
                    elif category == 'SP':
                        # SP cards get highest price
                        card_info = max(valid_prices, key=lambda x: x.get('price_yen', 0))
                    else:
                        # For other categories, use the first valid result
                        card_info = valid_prices[0]
                    
                    current_price_yen = card_info.get('price_yen', 0)
                    current_price_sgd = current_price_yen * JPY_TO_SGD_RATE
                else:
                    # No valid prices found, use original data but set price to 0
                    card_info = price_data[0]
                    current_price_yen = 0
                    current_price_sgd = 0
                
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
                    category=category,
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

@inventory_bp.route('/add_with_ai', methods=['GET', 'POST'])
def add_inventory_card_with_ai():
    """Add cards to inventory using AI image analysis"""
    if request.method == 'POST':
        from chatbot_service import get_card_details_from_ai_multimodal
        import os
        from werkzeug.utils import secure_filename
        
        user_description = request.form.get('card_description', '').strip()
        uploaded_files = request.files.getlist('card_image')
        
        # Validate input
        if not user_description and not any(file.filename for file in uploaded_files):
            flash("Please provide a card description or upload at least one image.", "error")
            return redirect(url_for('inventory.add_inventory_card_with_ai'))
        
        # Process uploaded images
        image_paths = []
        try:
            for card_image in uploaded_files:
                if card_image and card_image.filename != '':
                    # Create upload directory
                    from flask import current_app
                    upload_folder = os.path.join(current_app.instance_path, 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    # Save file securely
                    filename = secure_filename(card_image.filename)
                    if os.path.exists(os.path.join(upload_folder, filename)):
                        # Add timestamp to avoid conflicts
                        name, ext = os.path.splitext(filename)
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                        filename = f"{name}_{timestamp}{ext}"
                    
                    image_path = os.path.join(upload_folder, filename)
                    card_image.save(image_path)
                    image_paths.append(image_path)
            
            # Get card details from AI
            card_data_list = get_card_details_from_ai_multimodal(user_description, image_paths)
            
            # Clean up temporary files
            for path in image_paths:
                if os.path.exists(path):
                    os.remove(path)
            
            # Handle AI response errors
            if isinstance(card_data_list, dict) and 'error' in card_data_list:
                flash(f"AI Error: {card_data_list['error']}", "error")
                return redirect(url_for('inventory.add_inventory_card_with_ai'))
            
            if not isinstance(card_data_list, list) or not card_data_list:
                flash("AI could not identify any cards. Please try a different image or description.", "error")
                return redirect(url_for('inventory.add_inventory_card_with_ai'))
            
            # Process each card identified by AI
            added_cards = []
            for card_data in card_data_list:
                try:
                    card_number = card_data.get('card_number', '').strip()
                    if not card_number:
                        continue
                    
                    # Auto-detect category: First from user description, then from rarity
                    category = detect_category_from_text(user_description)
                    
                    if not category:
                        # Fall back to rarity-based detection
                        rarity = card_data.get('rarity', '')
                        if rarity.upper() in ['SEC', 'SECRET']:
                            category = 'SEC'
                        elif rarity.upper() in ['SR', 'SUPER RARE']:
                            category = 'SR'
                        elif rarity.upper() in ['L', 'LEADER']:
                            category = 'AA LDR'
                        else:
                            category = 'Regular'
                    
                    print(f"Auto-detected category: {category} (from description: '{user_description}')")
                    
                    # Fetch live pricing data (get all variants) - keep in JPY
                    price_data = get_yuyutei_prices_by_card_number(card_number)
                    current_price_yen = 0
                    current_price_sgd = 0
                    
                    if price_data and len(price_data) > 0:
                        # Filter for reasonable prices (between ¥50 and ¥50000)
                        valid_prices = [p for p in price_data if 50 <= p.get('price_yen', 0) <= 50000]
                        if valid_prices:
                            # Priority order for highest price selection:
                            # 1. Mangas (ALWAYS highest price - top priority)
                            # 2. SP (second highest value)
                            # 3. Others use first result
                            if category == 'Mangas':
                                # Manga cards ALWAYS get the absolute highest price
                                selected_card = max(valid_prices, key=lambda x: x.get('price_yen', 0))
                                current_price_yen = selected_card.get('price_yen', 0)
                                print(f"Manga card detected - using HIGHEST price: ¥{current_price_yen:,}")
                            elif category == 'SP':
                                # SP cards get highest price
                                selected_card = max(valid_prices, key=lambda x: x.get('price_yen', 0))
                                current_price_yen = selected_card.get('price_yen', 0)
                            else:
                                current_price_yen = valid_prices[0].get('price_yen', 0)
                            current_price_sgd = current_price_yen * JPY_TO_SGD_RATE  # For display only
                    
                    # Convert purchase price - focus on JPY
                    purchase_price_original = float(card_data.get('purchase_price_original', 0))
                    original_currency = card_data.get('original_currency', 'JPY')
                    
                    if original_currency == 'JPY':
                        purchase_price_yen = purchase_price_original
                        purchase_price_sgd = purchase_price_original * JPY_TO_SGD_RATE  # For display only
                    else:
                        # If not JPY, assume it was already in JPY (since Yuyu-tei is JPY)
                        purchase_price_yen = purchase_price_original
                        purchase_price_sgd = purchase_price_original * JPY_TO_SGD_RATE
                    
                    # Category already determined above
                    
                    # Create inventory card
                    new_card = InventoryCard(
                        name=card_data.get('name', 'Unknown Card'),
                        set_name=card_data.get('set_name', ''),
                        card_number=card_number,
                        rarity=card_data.get('rarity', ''),
                        color=card_data.get('color', ''),
                        quantity=int(card_data.get('quantity', 1)),
                        purchase_price_yen=purchase_price_yen,
                        purchase_price_sgd=purchase_price_sgd,
                        current_price_yen=current_price_yen,
                        current_price_sgd=current_price_sgd,
                        condition='Near Mint',  # Default for AI-added cards
                        category=category,
                        notes=f'Added via AI on {datetime.now().strftime("%Y-%m-%d")}',
                        image_url=card_data.get('image_url', ''),
                        last_price_update=datetime.utcnow()
                    )
                    
                    db.session.add(new_card)
                    db.session.flush()  # Get the ID
                    
                    # Create price history entry
                    if current_price_yen > 0:
                        price_entry = PriceHistory(
                            inventory_card_id=new_card.id,
                            price_yen=current_price_yen,
                            price_sgd=current_price_sgd,
                            jpy_to_sgd_rate=JPY_TO_SGD_RATE
                        )
                        db.session.add(price_entry)
                    
                    added_cards.append(new_card.name)
                    
                except Exception as e:
                    print(f"Error processing card {card_data.get('name', 'Unknown')}: {e}")
                    continue
            
            # Commit all changes
            if added_cards:
                db.session.commit()
                flash(f"Successfully added {len(added_cards)} cards to inventory: {', '.join(added_cards)}", "success")
            else:
                flash("No cards could be processed successfully.", "error")
            
            return redirect(url_for('inventory.inventory_list'))
            
        except Exception as e:
            db.session.rollback()
            # Clean up files in case of error
            for path in image_paths:
                if os.path.exists(path):
                    os.remove(path)
            flash(f"Error processing request: {str(e)}", "error")
            return redirect(url_for('inventory.add_inventory_card_with_ai'))
    
    return render_template('add_inventory_card_with_ai.html')

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
        latest_price = price_history[0].price_yen
        oldest_price = price_history[-1].price_yen
        price_change = latest_price - oldest_price
        price_change_percentage = (price_change / oldest_price * 100) if oldest_price > 0 else 0
        
        # Find highest and lowest prices in the period
        all_prices = [p.price_yen for p in price_history]
        highest_price = max(all_prices)
        lowest_price = min(all_prices)
    else:
        price_change = 0
        price_change_percentage = 0
        highest_price = card.current_price_yen
        lowest_price = card.current_price_yen
    
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
                # Filter for reasonable prices (between ¥50 and ¥50000)
                valid_prices = [p for p in price_data if 50 <= p.get('price_yen', 0) <= 50000]
                
                if valid_prices:
                    # Priority order for highest price selection:
                    # 1. Mangas (ALWAYS highest price - top priority)
                    # 2. SP (second highest value) 
                    # 3. Others use first result
                    if card.category == 'Mangas':
                        # Manga cards ALWAYS get the absolute highest price
                        selected_card = max(valid_prices, key=lambda x: x.get('price_yen', 0))
                        current_price_yen = selected_card.get('price_yen', 0)
                        print(f"Manga card detected - using HIGHEST price: ¥{current_price_yen:,}")
                    elif card.category == 'SP':
                        # SP cards get highest price
                        selected_card = max(valid_prices, key=lambda x: x.get('price_yen', 0))
                        current_price_yen = selected_card.get('price_yen', 0)
                    else:
                        current_price_yen = valid_prices[0].get('price_yen', 0)
                else:
                    current_price_yen = 0
                    
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
        card.category = request.form.get('category', card.category)
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
    """Show inventory analytics and trends with category breakdown"""
    cards = InventoryCard.query.all()
    
    # Calculate overall metrics (using JPY)
    total_cards = sum(card.quantity for card in cards)
    total_purchase_value = sum(card.purchase_price_yen * card.quantity for card in cards)
    total_current_value = sum(card.current_price_yen * card.quantity for card in cards)
    
    # Category breakdown
    categories = ['Mangas', 'SP', 'AA LDR', 'SEC', 'AA', 'SR', 'Regular']
    category_breakdown = {}
    
    for category in categories:
        category_cards = [card for card in cards if card.category == category]
        if category_cards:
            cat_purchase_value = sum(card.purchase_price_yen * card.quantity for card in category_cards)
            cat_current_value = sum(card.current_price_yen * card.quantity for card in category_cards)
            cat_gain_loss = cat_current_value - cat_purchase_value
            cat_gain_loss_pct = (cat_gain_loss / cat_purchase_value * 100) if cat_purchase_value > 0 else 0
            
            category_breakdown[category] = {
                'cards': len(category_cards),
                'total_quantity': sum(card.quantity for card in category_cards),
                'purchase_value': cat_purchase_value,
                'current_value': cat_current_value,
                'gain_loss': cat_gain_loss,
                'gain_loss_percentage': cat_gain_loss_pct
            }
    
    # Top gainers and losers
    card_performances = []
    for card in cards:
        if card.purchase_price_yen > 0:
            gain_loss = (card.current_price_yen - card.purchase_price_yen) * card.quantity
            gain_loss_percentage = (card.current_price_yen - card.purchase_price_yen) / card.purchase_price_yen * 100
            card_performances.append({
                'card': card,
                'gain_loss': gain_loss,
                'gain_loss_percentage': gain_loss_percentage
            })
    
    # Sort by percentage gain/loss
    card_performances.sort(key=lambda x: x['gain_loss_percentage'], reverse=True)
    top_gainers = card_performances[:5]
    top_losers = card_performances[-5:]
    
    # Find the most valuable card (highest current price in yen)
    most_valuable_card = max(cards, key=lambda x: x.current_price_yen) if cards else None

    return render_template('inventory_analytics.html',
                         total_cards=total_cards,
                         total_purchase_value=total_purchase_value,
                         total_current_value=total_current_value,
                         category_breakdown=category_breakdown,
                         top_gainers=top_gainers,
                         top_losers=top_losers,
                         most_valuable_card=most_valuable_card)