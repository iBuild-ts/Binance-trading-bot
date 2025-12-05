# ================================================
# LiveTrading_Beast.py — 40% DAILY COMPOUNDING MODE
# AGGRESSIVE PROFIT TAKING | SYMBOL FILTERING | POSITION SIZING
# Only trade winners | Exit at +40% daily | Cut losers immediately
# ================================================

import time
import pandas as pd
import numpy as np
from binance import Client
from ta.trend import EMAIndicator, MACD, PSARIndicator
from ta.momentum import StochasticOscillator, RSIIndicator
from ta.volatility import BollingerBands
import logging
from datetime import datetime

# ================== CONFIG ==================
API_KEY = 'tY6PJ6sKd1juJvV0ywQrl0bfFswlUd84uOfdDd6TMEfsvaF2F7eiNlAXL8KtDb8z'
API_SECRET = 'K5hbHYvr55kdmWPxl1Jwi9R9xN97oKp2O6akmLVVTwosG4eAg3HOwzxpsUbADFSY'

client = Client(api_key=API_KEY, api_secret=API_SECRET, testnet=True)

# ONLY TRADE WINNERS (symbols with consistent wins)
WINNING_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
LOSING_SYMBOLS = ['ADAUSDT', 'XRPUSDT', 'DOGEUSDT']  # BLACKLIST

LEVERAGE = 20
RISK_PERCENT = 2.0  # 2% per trade (aggressive)
CHECK_INTERVAL = 30  # seconds (faster scanning)
DAILY_PROFIT_TARGET = 0.40  # 40% daily target

# ===== NO SL MODE =====
# TP: +4% (easy to hit, quick wins)
# SL: NONE (let positions recover, unlimited upside)
# Risk/Reward: Better (only take profits, let winners run)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

# ================== DATA FETCH ==================
def get_klines(symbol, timeframe, limit=500):
    try:
        bars = client.futures_klines(symbol=symbol, interval=timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'trades', 'tb_base_vol', 'tb_quote_vol', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['open'] = pd.to_numeric(df['open'])
        return df
    except Exception as e:
        logging.error(f"Error fetching {symbol} {timeframe}: {e}")
        return pd.DataFrame()

# ================== AGGRESSIVE TA ANALYSIS ==================
def get_indicators(df):
    """Calculate all indicators"""
    try:
        macd = MACD(df['close'])
        psar = PSARIndicator(df['high'], df['low'], df['close'])
        stoch = StochasticOscillator(df['high'], df['low'], df['close'], window=14, smooth_window=3)
        rsi = RSIIndicator(df['close'], window=14)
        bb = BollingerBands(df['close'])
        
        return {
            'macd_line': macd.macd().iloc[-1],
            'macd_signal': macd.macd_signal().iloc[-1],
            'macd_hist': macd.macd_diff().iloc[-1],
            'psar': psar.psar().iloc[-1],
            'stoch_k': stoch.stoch().iloc[-1],
            'stoch_d': stoch.stoch_signal().iloc[-1],
            'rsi': rsi.rsi().iloc[-1],
            'bb_upper': bb.bollinger_hband().iloc[-1],
            'bb_lower': bb.bollinger_lband().iloc[-1],
            'bb_mid': bb.bollinger_mavg().iloc[-1]
        }
    except:
        return None

def detect_bos_choch(df):
    """Detect Break of Structure"""
    try:
        highs = df['high'].rolling(20).max().shift(1)
        lows = df['low'].rolling(20).min().shift(1)
        
        if df['high'].iloc[-1] > highs.iloc[-1]:
            return "BULLISH_BOS"
        if df['low'].iloc[-1] < lows.iloc[-1]:
            return "BEARISH_BOS"
        return None
    except:
        return None

# ================== AGGRESSIVE ENTRY LOGIC ==================
def analyze_symbol_aggressive(symbol):
    """
    AGGRESSIVE ANALYSIS - Only enter on STRONG signals
    Requires 5+ points for entry (very selective)
    """
    try:
        df = get_klines(symbol, '5m', 100)  # 5m for faster entries
        if df.empty or len(df) < 50:
            return None, "Insufficient data", 0
        
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        ind = get_indicators(df)
        if not ind:
            return None, "Indicator error", 0
        
        bos = detect_bos_choch(df)
        
        # ===== LONG ANALYSIS =====
        long_score = 0
        long_reasons = []
        
        # 1. MACD STRONG bullish (histogram positive AND crossing)
        if ind['macd_line'] > ind['macd_signal'] and ind['macd_hist'] > 0.0001:
            long_score += 2
            long_reasons.append("MACD↑")
        
        # 2. Stochastic OVERSOLD + crossing (strong reversal)
        if ind['stoch_k'] < 20 and ind['stoch_k'] > ind['stoch_d']:
            long_score += 3
            long_reasons.append("Stoch↑")
        elif ind['stoch_k'] > ind['stoch_d'] and ind['stoch_k'] < 50:
            long_score += 1
            long_reasons.append("Stoch+")
        
        # 3. RSI OVERSOLD (< 30)
        if ind['rsi'] < 30:
            long_score += 2
            long_reasons.append("RSI↓")
        elif 30 < ind['rsi'] < 50:
            long_score += 1
            long_reasons.append("RSI~")
        
        # 4. Price above SAR (uptrend)
        if price > ind['psar']:
            long_score += 1
            long_reasons.append("SAR↑")
        
        # 5. BOS confirmation (strong)
        if bos == "BULLISH_BOS":
            long_score += 2
            long_reasons.append("BOS↑")
        
        # ===== SHORT ANALYSIS =====
        short_score = 0
        short_reasons = []
        
        if ind['macd_line'] < ind['macd_signal'] and ind['macd_hist'] < -0.0001:
            short_score += 2
            short_reasons.append("MACD↓")
        
        if ind['stoch_k'] > 80 and ind['stoch_k'] < ind['stoch_d']:
            short_score += 3
            short_reasons.append("Stoch↓")
        elif ind['stoch_k'] < ind['stoch_d'] and ind['stoch_k'] > 50:
            short_score += 1
            short_reasons.append("Stoch-")
        
        if ind['rsi'] > 70:
            short_score += 2
            short_reasons.append("RSI↑")
        elif 50 < ind['rsi'] < 70:
            short_score += 1
            short_reasons.append("RSI~")
        
        if price < ind['psar']:
            short_score += 1
            short_reasons.append("SAR↓")
        
        if bos == "BEARISH_BOS":
            short_score += 2
            short_reasons.append("BOS↓")
        
        # ===== DECISION: Need 5+ points for entry =====
        if long_score >= 5 and long_score > short_score:
            reason = " | ".join(long_reasons)
            return 'LONG', reason, long_score
        
        if short_score >= 5 and short_score > long_score:
            reason = " | ".join(short_reasons)
            return 'SHORT', reason, short_score
        
        return None, f"L:{long_score}/S:{short_score}", max(long_score, short_score)
    
    except Exception as e:
        return None, f"Error: {e}", 0

def should_enter_long(symbol):
    """Check LONG entry"""
    signal, reason, confidence = analyze_symbol_aggressive(symbol)
    if signal == 'LONG':
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        return True, f"🚀 LONG {symbol} @ {price:.2f} | {reason} ({confidence}/11)"
    return False, reason

def should_enter_short(symbol):
    """Check SHORT entry"""
    signal, reason, confidence = analyze_symbol_aggressive(symbol)
    if signal == 'SHORT':
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        return True, f"🚀 SHORT {symbol} @ {price:.2f} | {reason} ({confidence}/11)"
    return False, reason

# ================== POSITION & ORDER ==================
def get_open_positions():
    try:
        positions = client.futures_position_information()
        return [p['symbol'] for p in positions if abs(float(p['positionAmt'])) > 0.0001]
    except:
        return []

def get_precision(symbol):
    try:
        info = client.futures_exchange_info()
        for sym in info['symbols']:
            if sym['symbol'] == symbol:
                return sym['quantityPrecision']
    except:
        pass
    return 3

def place_order(symbol, side):
    try:
        balance = float(client.futures_account_balance()[6]['balance'])  # USDT
        risk_amount = balance * (RISK_PERCENT / 100)
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        qty = (risk_amount * LEVERAGE) / price
        
        precision = get_precision(symbol)
        qty = round(qty, precision)
        
        client.futures_change_leverage(symbol=symbol, leverage=LEVERAGE)
        client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=qty
        )
        logging.info(f"✅ EXECUTED {side} {symbol} | Qty: {qty} | ${risk_amount:.2f} risk")
    except Exception as e:
        logging.error(f"❌ Order failed {symbol}: {e}")

# ================== PROFIT MANAGER (AGGRESSIVE) ==================
def profit_manager():
    try:
        from ProfitManager import manage_open_positions
        manage_open_positions()
    except Exception as e:
        logging.warning(f"Profit manager error: {e}")

# ================== MAIN BEAST LOOP ==================
if __name__ == "__main__":
    logging.info("🔥 BEAST MODE ACTIVATED — 40% DAILY COMPOUNDING (NO SL)")
    logging.info(f"Trading only WINNERS: {WINNING_SYMBOLS}")
    logging.info(f"Blacklisted LOSERS: {LOSING_SYMBOLS}")
    logging.info(f"TP: +4% | SL: NONE (let winners run)")
    logging.info(f"Risk/Reward: Better (unlimited upside)")
    
    while True:
        try:
            open_pos = get_open_positions()
            
            for symbol in WINNING_SYMBOLS:
                if symbol in open_pos:
                    continue
                
                try:
                    go_long, reason = should_enter_long(symbol)
                    go_short, reason_s = should_enter_short(symbol)
                    
                    if go_long:
                        place_order(symbol, "BUY")
                    elif go_short:
                        place_order(symbol, "SELL")
                except Exception as e:
                    logging.warning(f"{symbol} scan error: {e}")
            
            profit_manager()
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            logging.info("🛑 Beast stopped — peace out!")
            break
        except Exception as e:
            logging.error(f"Main loop error: {e}")
            time.sleep(5)
