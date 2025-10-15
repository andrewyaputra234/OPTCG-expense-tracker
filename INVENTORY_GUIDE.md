# Inventory System Setup and Usage Guide

## Overview
The new Inventory System allows you to track your personal card collection with daily price monitoring and trend analysis. This is separate from your existing sales-focused collections.

## Key Features
- **Live Price Fetching**: Automatically fetches current prices from Yuyu-tei when adding cards
- **Daily Price History**: Tracks price changes over time for trend analysis
- **Portfolio Analytics**: Shows total value, gains/losses, and performance metrics
- **Price Charts**: Visual representation of price trends for each card
- **Automated Updates**: Background service to update all card prices daily

## Getting Started

### 1. Navigate to Your Inventory
- Click "My Inventory" in the navigation menu
- URL: http://127.0.0.1:5000/inventory/

### 2. Add Your First Card
1. Click "Add Card" button
2. Enter the card number (e.g., OP01-025)
3. Set quantity and purchase details
4. The system will automatically fetch current market price
5. Click "Add to Inventory"

### 3. View Card Details
- Click on any card name to see detailed information
- View price history charts (last 30 days)
- See performance metrics (profit/loss)
- Track price trends over time

### 4. Analytics Dashboard
- Click "Analytics" to see portfolio overview
- View top performers and underperformers
- See total portfolio value and ROI

## Daily Price Updates

### Automatic Updates
The system includes a price updater service that can run daily:

```bash
python price_updater.py
```

### Setting Up Scheduled Updates (Windows)
1. Use the provided batch file: `update_inventory_prices.bat`
2. Set up Windows Task Scheduler to run it daily:
   - Open Task Scheduler
   - Create Basic Task
   - Set trigger to "Daily"
   - Set action to start the batch file
   - Set time (recommended: early morning)

### Manual Price Updates
- In the inventory list, click "Update All Prices"
- This fetches the latest prices for all cards
- Updates are saved to price history

## System Architecture

### Database Tables
- **inventory_card**: Your card collection with purchase and current price info
- **price_history**: Daily price records for trend tracking

### Price Sources
- Primary: Yuyu-tei (yuyutei.jp)
- Currency: Japanese Yen (JPY) converted to Singapore Dollars (SGD)
- Exchange Rate: Configurable (currently ~0.009)

### Data Retention
- Price history kept for 90 days (configurable)
- Older records automatically cleaned up

## Usage Tips

1. **Accurate Card Numbers**: Use exact card numbers (e.g., OP01-025) for best results
2. **Regular Updates**: Run price updates daily for accurate trend data
3. **Portfolio Tracking**: Use analytics to monitor investment performance
4. **Condition Tracking**: Record card conditions for accurate valuations

## Troubleshooting

### Common Issues
1. **Price not found**: Verify card number format and availability on Yuyu-tei
2. **Update failures**: Check internet connection and Yuyu-tei accessibility
3. **Database errors**: Ensure proper database setup and permissions

### Support
- Check application logs for error details
- Verify network connectivity for price fetching
- Ensure all required dependencies are installed

## Future Enhancements
- Multiple price source integration
- Email notifications for significant price changes
- Export functionality for external analysis
- Mobile-responsive interface improvements
- Advanced filtering and search capabilities