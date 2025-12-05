# MAIN_LOOP_TEMPLATE.py
# Template showing how to integrate anti-degen modules into your main trading loop
# Copy this pattern into your LiveTrading.py or LiveTrading_Beast.py

import logging
import time
from datetime import datetime

# ============ ANTI-DEGEN IMPORTS ============
from NewsFilter import should_pause_trading
from DailyLimits import DailyLimitsManager
from ProfitManager import manage_open_positions

# ============ YOUR EXISTING IMPORTS ============
from LiveTradingConfig import API_KEY, API_SECRET, testnet, trading_strategy
from binance import Client
# ... other imports ...

# ============ SETUP LOGGING ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ============ INITIALIZE CLIENT & MANAGERS ============
client = Client(api_key=API_KEY, api_secret=API_SECRET, testnet=testnet)
daily_limits = DailyLimitsManager(API_KEY, API_SECRET, testnet)

# ============ MAIN TRADING LOOP ============
def main_trading_loop():
    """
    Main trading loop with anti-degen protections
    """
    logging.info("🚀 Starting trading bot with anti-degen protections...")
    
    loop_count = 0
    
    while True:
        try:
            loop_count += 1
            
            # ============ STEP 1: CHECK NEWS FILTER ============
            should_pause_news, news_reason = should_pause_trading()
            if should_pause_news:
                logging.warning(f"[NEWS FILTER] {news_reason}")
                time.sleep(300)  # Wait 5 minutes before checking again
                continue
            
            # ============ STEP 2: CHECK DAILY LIMITS ============
            should_pause_limits, limits_reason = daily_limits.check_daily_limits()
            if should_pause_limits:
                logging.warning(f"[DAILY LIMITS] {limits_reason}")
                time.sleep(60)  # Wait 1 minute before checking again
                continue
            
            # ============ STEP 3: MANAGE OPEN POSITIONS ============
            # This handles profit taking (10% TP, 4% partial exit)
            manage_open_positions()
            
            # ============ STEP 4: YOUR TRADING LOGIC ============
            # Insert your existing trading logic here
            # Example:
            # - Get latest candles
            # - Run strategy analysis
            # - Generate signals
            # - Place new orders
            
            # Placeholder for your trading logic
            if loop_count % 100 == 0:
                logging.info(f"[LOOP {loop_count}] Trading active, no issues")
            
            # ============ STEP 5: SLEEP ============
            time.sleep(1)  # Adjust based on your strategy
        
        except KeyboardInterrupt:
            logging.info("🛑 Bot stopped by user")
            break
        
        except Exception as e:
            logging.error(f"❌ Error in main loop: {e}")
            time.sleep(5)  # Wait before retrying

# ============ EXAMPLE: INTEGRATION WITH EXISTING CODE ============
"""
If you have existing code like this:

    while True:
        try:
            # Get signals
            signals = get_signals()
            
            # Place trades
            for signal in signals:
                place_trade(signal)
            
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")

Change it to:

    while True:
        try:
            # ============ ADD THESE 3 CHECKS ============
            # 1. News filter
            should_pause_news, _ = should_pause_trading()
            if should_pause_news:
                time.sleep(300)
                continue
            
            # 2. Daily limits
            should_pause_limits, _ = daily_limits.check_daily_limits()
            if should_pause_limits:
                time.sleep(60)
                continue
            
            # 3. Manage profits
            manage_open_positions()
            
            # ============ YOUR EXISTING CODE ============
            # Get signals
            signals = get_signals()
            
            # Place trades
            for signal in signals:
                place_trade(signal)
            
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
"""

# ============ MONITORING FUNCTIONS ============
def print_daily_status():
    """Print current daily limits status"""
    status = daily_limits.get_status()
    print("\n" + "="*60)
    print("📊 DAILY STATUS")
    print("="*60)
    print(f"Date: {status['date']}")
    print(f"Trades: {status['trades_count']}/{status['max_trades']}")
    print(f"Daily PnL: {status['daily_pnl_percent']:+.2f}%")
    print(f"Target: {status['daily_pnl_target']:.1f}% | Limit: {status['daily_loss_limit']:.1f}%")
    print(f"Paused: {status['is_paused']}")
    if status['pause_reason']:
        print(f"Reason: {status['pause_reason']}")
    print("="*60 + "\n")

def print_trade_history():
    """Print today's trades"""
    status = daily_limits.get_status()
    if not status['trades']:
        print("No trades today")
        return
    
    print("\n" + "="*60)
    print("📈 TODAY'S TRADES")
    print("="*60)
    for i, trade in enumerate(status['trades'], 1):
        print(f"{i}. {trade['symbol']} {trade['direction']}")
        print(f"   PnL: {trade['pnl_usdt']:+.2f} USDT ({trade['pnl_percent']:+.2f}%)")
        print(f"   Time: {trade['timestamp']}")
    print("="*60 + "\n")

# ============ RUN THE BOT ============
if __name__ == "__main__":
    try:
        main_trading_loop()
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped")
        print_daily_status()
        print_trade_history()
