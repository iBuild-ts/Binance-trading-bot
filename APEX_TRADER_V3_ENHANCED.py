#!/usr/bin/env python3
"""
APEX_TRADER_V3_ENHANCED.py
Uses ENHANCED_STRATEGY.py with professional-grade indicators
- RSI, MACD, Bollinger Bands, ATR, ADX, Stochastic
- Risk management with position sizing
- Daily loss limits and consecutive loss tracking
- Proper entry/exit price tracking
"""

import time
import pandas as pd
import numpy as np
from binance import Client
import requests
import json
from datetime import datetime, date
import logging
import os
from urllib3.exceptions import MaxRetryError, NameResolutionError
from dotenv import load_dotenv
import hashlib

# Import enhanced strategy
from ENHANCED_STRATEGY import enhanced_momentum_strategy, calculate_position_size, calculate_take_profit

# Load environment variables
load_dotenv()

# ================== CONFIG ==================
API_KEY = os.getenv('BINANCE_API_KEY', '')
API_SECRET = os.getenv('BINANCE_API_SECRET', '')

if not API_KEY or not API_SECRET:
    raise ValueError("❌ CRITICAL: API keys not found in .env file")

client = Client(api_key=API_KEY, api_secret=API_SECRET, testnet=True)

# Trading parameters
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
LEVERAGE = 20
ORDER_SIZE = 10  # USDT
MAX_TRADES_PER_DAY = 10
DAILY_LOSS_LIMIT = -3.0  # Stop trading after -3% daily loss
MAX_CONSECUTIVE_LOSSES = 3  # Stop after 3 consecutive losses
TAKE_PROFIT_PERCENT = 10.3  # Aim for +10.3% to net +10% after fees
STOP_LOSS_PERCENT = 8.0
MIN_SIGNAL_STRENGTH = 60  # Only trade signals with 60%+ strength

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ================== STATE TRACKING ==================
state = {
    "trades_today": 0,
    "daily_pnl": 0.0,
    "last_reset": date.today(),
    "active_trades": {},
    "consecutive_losses": 0,
    "trading_paused": False,
    "pause_reason": "",
    "executed_signals": set(),
    "total_pnl": 0.0,
    "win_count": 0,
    "loss_count": 0
}

# ================== TRADE LOG ==================
TRADE_LOG_FILE = 'apex_trades_v3.csv'

def init_trade_log():
    """Initialize trade log with proper headers"""
    if not os.path.exists(TRADE_LOG_FILE):
        with open(TRADE_LOG_FILE, 'w') as f:
            f.write('Timestamp,Symbol,Direction,Entry_Price,Exit_Price,Quantity,Margin_USDT,PNL_USDT,PNL_Percent,Exit_Reason,Duration_Minutes,Signal_Strength,Reasons\n')

def log_trade(symbol, direction, entry_price, exit_price, quantity, margin, pnl_usdt, pnl_pct, exit_reason, duration, signal_strength, reasons):
    """Log trade with full forensic details"""
    with open(TRADE_LOG_FILE, 'a') as f:
        reason_str = '|'.join(reasons) if reasons else 'N/A'
        f.write(f'{datetime.now().isoformat()},{symbol},{direction},{entry_price:.2f},{exit_price:.2f},{quantity:.4f},{margin:.2f},{pnl_usdt:.2f},{pnl_pct:.2f}%,{exit_reason},{duration},{signal_strength:.1f},"{reason_str}"\n')

# ================== DUPLICATE PREVENTION ==================
def get_signal_hash(symbol, direction, entry_price):
    """Create unique hash for each signal to prevent duplicates"""
    signal_str = f"{symbol}_{direction}_{entry_price:.2f}_{datetime.now().minute}"
    return hashlib.md5(signal_str.encode()).hexdigest()[:8]

def is_duplicate_signal(symbol, direction, entry_price):
    """Check if this signal was already executed"""
    signal_hash = get_signal_hash(symbol, direction, entry_price)
    if signal_hash in state["executed_signals"]:
        logger.warning(f"⚠️  DUPLICATE SIGNAL BLOCKED: {symbol} {direction} @ {entry_price}")
        return True
    state["executed_signals"].add(signal_hash)
    return False

# ================== DAILY LIMITS ==================
def check_daily_limits():
    """Check if trading should be paused due to daily limits"""
    
    # Reset daily stats if new day
    if date.today() != state["last_reset"]:
        state["trades_today"] = 0
        state["daily_pnl"] = 0.0
        state["consecutive_losses"] = 0
        state["last_reset"] = date.today()
        state["executed_signals"].clear()
        logger.info("📅 Daily reset — new trading day started")
    
    # Check daily loss limit
    if state["daily_pnl"] <= DAILY_LOSS_LIMIT:
        state["trading_paused"] = True
        state["pause_reason"] = f"Daily loss limit hit: {state['daily_pnl']:.2f}%"
        logger.error(f"🛑 TRADING PAUSED: {state['pause_reason']}")
        return False
    
    # Check max trades per day
    if state["trades_today"] >= MAX_TRADES_PER_DAY:
        state["trading_paused"] = True
        state["pause_reason"] = f"Max {MAX_TRADES_PER_DAY} trades/day reached"
        logger.warning(f"⚠️  {state['pause_reason']}")
        return False
    
    # Check consecutive losses
    if state["consecutive_losses"] >= MAX_CONSECUTIVE_LOSSES:
        state["trading_paused"] = True
        state["pause_reason"] = f"{MAX_CONSECUTIVE_LOSSES} consecutive losses — cooling off"
        logger.warning(f"❄️  {state['pause_reason']}")
        return False
    
    return True

# ================== RETRY LOGIC ==================
def retry_with_backoff(func, max_retries=3, base_delay=1):
    """Retry function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except (MaxRetryError, NameResolutionError, requests.ConnectionError, 
                ConnectionError, TimeoutError, Exception) as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Connection error (attempt {attempt + 1}/{max_retries}), retrying in {delay}s")
                time.sleep(delay)
            else:
                logger.error(f"Max retries exceeded: {e}")
                return None
    return None

# ================== FETCH MARKET DATA ==================
def get_klines(symbol, interval='1m', limit=100):
    """Fetch candlestick data with retry logic"""
    def _fetch():
        return client.futures_klines(symbol=symbol, interval=interval, limit=limit)
    
    klines = retry_with_backoff(_fetch)
    if not klines:
        return None
    
    df = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 
                                       'close_time', 'quote_asset_volume', 'number_of_trades',
                                       'taker_buy_base', 'taker_buy_quote', 'ignore'])
    
    # Convert to numeric
    for col in ['close', 'open', 'high', 'low', 'volume']:
        df[col] = pd.to_numeric(df[col])
    
    return df

# ================== PLACE ORDER ==================
def place_order(symbol, direction, entry_price, quantity, stop_loss_price, take_profit_price):
    """Place order with proper error handling and price tracking"""
    
    try:
        if direction == "LONG":
            order = client.futures_create_order(
                symbol=symbol,
                side='BUY',
                type='LIMIT',
                timeInForce='GTC',
                quantity=quantity,
                price=entry_price
            )
        else:  # SHORT
            order = client.futures_create_order(
                symbol=symbol,
                side='SELL',
                type='LIMIT',
                timeInForce='GTC',
                quantity=quantity,
                price=entry_price
            )
        
        logger.info(f"✅ Order placed: {symbol} {direction} @ {entry_price:.2f} qty={quantity:.4f}")
        logger.info(f"   SL: {stop_loss_price:.2f} | TP: {take_profit_price:.2f}")
        return order
    
    except Exception as e:
        logger.error(f"❌ Order failed: {symbol} {direction} — {e}")
        return None

# ================== MAIN TRADING LOOP ==================
def run_trading_loop():
    """Main trading loop with enhanced strategy"""
    
    init_trade_log()
    logger.info("🚀 APEX TRADER V3 ENHANCED — Starting")
    logger.info(f"   Leverage: {LEVERAGE}x")
    logger.info(f"   Order Size: {ORDER_SIZE} USDT")
    logger.info(f"   Min Signal Strength: {MIN_SIGNAL_STRENGTH}%")
    logger.info(f"   Daily Loss Limit: {DAILY_LOSS_LIMIT}%")
    logger.info(f"   Max Consecutive Losses: {MAX_CONSECUTIVE_LOSSES}")
    
    iteration = 0
    while True:
        iteration += 1
        
        try:
            # Check daily limits
            if not check_daily_limits():
                logger.warning(f"Trading paused: {state['pause_reason']}")
                time.sleep(60)
                continue
            
            logger.info(f"\n{'='*70}")
            logger.info(f"Iteration {iteration} | Daily PnL: {state['daily_pnl']:+.2f}% | Trades: {state['trades_today']}/{MAX_TRADES_PER_DAY}")
            logger.info(f"Wins: {state['win_count']} | Losses: {state['loss_count']} | Consecutive Losses: {state['consecutive_losses']}")
            logger.info(f"{'='*70}")
            
            # Analyze each symbol
            for symbol in SYMBOLS:
                logger.info(f"\n📊 Analyzing {symbol}...")
                
                # Get market data
                df = get_klines(symbol, interval='1m', limit=100)
                if df is None:
                    logger.warning(f"   ⚠️  Failed to fetch data for {symbol}")
                    continue
                
                # Get current price
                current_price = float(df['close'].iloc[-1])
                logger.info(f"   Current Price: ${current_price:.2f}")
                
                # Generate signal using enhanced strategy
                direction, signal_strength, reasons = enhanced_momentum_strategy(
                    df, 
                    current_idx=len(df)-1,
                    symbol=symbol,
                    min_signal_strength=MIN_SIGNAL_STRENGTH
                )
                
                if direction == 0:
                    logger.info(f"   ➡️  No signal (strength: {signal_strength:.1f}%)")
                    continue
                
                # Check for duplicate
                if is_duplicate_signal(symbol, "LONG" if direction == 1 else "SHORT", current_price):
                    continue
                
                # Calculate position size and risk management
                quantity = ORDER_SIZE / current_price
                stop_loss_price = current_price * (1 - STOP_LOSS_PERCENT/100) if direction == 1 else current_price * (1 + STOP_LOSS_PERCENT/100)
                take_profit_price = calculate_take_profit(current_price, direction, risk_reward_ratio=2.0, stop_loss_price=stop_loss_price)
                
                # Place order
                order = place_order(
                    symbol, 
                    "LONG" if direction == 1 else "SHORT", 
                    current_price, 
                    quantity,
                    stop_loss_price,
                    take_profit_price
                )
                
                if order:
                    state["trades_today"] += 1
                    logger.info(f"   ✅ {'LONG' if direction == 1 else 'SHORT'} signal (strength: {signal_strength:.1f}%)")
                    logger.info(f"   Reasons: {', '.join(reasons[:3])}")
                
            
            # Wait before next iteration
            logger.info(f"\n⏳ Waiting 60 seconds before next analysis...")
            time.sleep(60)
        
        except Exception as e:
            logger.error(f"❌ Error in trading loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_trading_loop()
