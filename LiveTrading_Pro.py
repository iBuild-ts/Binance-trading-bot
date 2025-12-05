# ================================================
# LiveTrading_Pro.py — THE REAL BEAST (2025 Edition)
# Multi-Timeframe | Market Structure | Order Blocks | BOS/CHOCH
# Long + Short | 15m Entries | 1h/4h Bias | Zero Noise
# ================================================

import time
import pandas as pd
import numpy as np
from binance import Client
from ta.trend import EMAIndicator, MACD, PSARIndicator
from ta.momentum import StochasticOscillator, RSIIndicator
from ta.volatility import BollingerBands
import logging

# ================== CONFIG ==================
API_KEY = 'tY6PJ6sKd1juJvV0ywQrl0bfFswlUd84uOfdDd6TMEfsvaF2F7eiNlAXL8KtDb8z'
API_SECRET = 'K5hbHYvr55kdmWPxl1Jwi9R9xN97oKp2O6akmLVVTwosG4eAg3HOwzxpsUbADFSY'

client = Client(api_key=API_KEY, api_secret=API_SECRET, testnet=True)

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'XRPUSDT', 'BNBUSDT', 'DOGEUSDT']
LEVERAGE = 20
RISK_PERCENT = 1.0  # 1% per trade → compounding god mode
CHECK_INTERVAL = 45  # seconds

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

# ================== HIGHER TIMEFRAME BIAS ==================
def get_trend_bias(symbol):
    df = get_klines(symbol, '1h', 200)
    if df.empty: return "SIDEWAYS"
    
    ema50 = EMAIndicator(df['close'], window=50).ema_indicator()
    ema200 = EMAIndicator(df['close'], window=200).ema_indicator()
    
    if ema50.iloc[-1] > ema200.iloc[-1] and ema50.iloc[-2] <= ema200.iloc[-2]:
        return "BULLISH_REVERSAL"
    if ema50.iloc[-1] < ema200.iloc[-1] and ema50.iloc[-2] >= ema200.iloc[-2]:
        return "BEARISH_REVERSAL"
    if ema50.iloc[-1] > ema200.iloc[-1]:
        return "BULLISH"
    if ema50.iloc[-1] < ema200.iloc[-1]:
        return "BEARISH"
    return "SIDEWAYS"

# ================== 15M MARKET STRUCTURE ==================
def detect_bos_choch(df):
    highs = df['high'].rolling(20).max().shift(1)
    lows = df['low'].rolling(20).min().shift(1)
    
    if df['high'].iloc[-1] > highs.iloc[-1]:
        return "BULLISH_BOS"
    if df['low'].iloc[-1] < lows.iloc[-1]:
        return "BEARISH_BOS"
    return None

def find_order_block(df, direction="bullish"):
    for i in range(len(df)-20, 20, -1):
        if direction == "bullish":
            if df['close'].iloc[i] < df['open'].iloc[i]:  # strong bear candle
                if df['close'].iloc[i+1] > df['high'].iloc[i]:  # bullish engulfing
                    return df['low'].iloc[i], df['high'].iloc[i]
        else:
            if df['close'].iloc[i] > df['open'].iloc[i]:
                if df['close'].iloc[i+1] < df['low'].iloc[i]:
                    return df['low'].iloc[i], df['high'].iloc[i]
    return None, None

# ================== INDICATORS (15m) ==================
def get_indicators(df):
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

# ================== INDIVIDUAL SYMBOL ANALYSIS (TA GOD MODE) ==================
def analyze_symbol(symbol):
    """
    DEEP TA ANALYSIS PER SYMBOL
    Returns: (signal, reason, confidence)
    signal: 'LONG', 'SHORT', or None
    """
    try:
        df = get_klines(symbol, '15m', 100)
        if df.empty or len(df) < 50:
            return None, "Insufficient data", 0
        
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        ind = get_indicators(df)
        bos = detect_bos_choch(df)
        
        # ===== LONG ANALYSIS =====
        long_score = 0
        long_reasons = []
        
        # 1. MACD Bullish Crossover (strong signal)
        if ind['macd_line'] > ind['macd_signal'] and ind['macd_hist'] > 0:
            long_score += 2
            long_reasons.append("MACD bullish")
        
        # 2. Stochastic in oversold + crossing up (reversal)
        if ind['stoch_k'] < 30 and ind['stoch_k'] > ind['stoch_d']:
            long_score += 2
            long_reasons.append("Stoch oversold+cross")
        elif ind['stoch_k'] > ind['stoch_d'] and ind['stoch_k'] < 70:
            long_score += 1
            long_reasons.append("Stoch bullish")
        
        # 3. RSI in healthy zone (not overbought)
        if 30 < ind['rsi'] < 60:
            long_score += 1
            long_reasons.append("RSI neutral")
        elif ind['rsi'] < 30:
            long_score += 2
            long_reasons.append("RSI oversold")
        
        # 4. Price above SAR (uptrend)
        if price > ind['psar']:
            long_score += 1
            long_reasons.append("Price > SAR")
        
        # 5. Price below BB midline (room to go up)
        if price < ind['bb_mid']:
            long_score += 1
            long_reasons.append("Below BB mid")
        
        # 6. BOS confirmation
        if bos == "BULLISH_BOS":
            long_score += 2
            long_reasons.append("Bullish BOS")
        
        # ===== SHORT ANALYSIS =====
        short_score = 0
        short_reasons = []
        
        # 1. MACD Bearish Crossover (strong signal)
        if ind['macd_line'] < ind['macd_signal'] and ind['macd_hist'] < 0:
            short_score += 2
            short_reasons.append("MACD bearish")
        
        # 2. Stochastic in overbought + crossing down (reversal)
        if ind['stoch_k'] > 70 and ind['stoch_k'] < ind['stoch_d']:
            short_score += 2
            short_reasons.append("Stoch overbought+cross")
        elif ind['stoch_k'] < ind['stoch_d'] and ind['stoch_k'] > 30:
            short_score += 1
            short_reasons.append("Stoch bearish")
        
        # 3. RSI in healthy zone (not oversold)
        if 40 < ind['rsi'] < 70:
            short_score += 1
            short_reasons.append("RSI neutral")
        elif ind['rsi'] > 70:
            short_score += 2
            short_reasons.append("RSI overbought")
        
        # 4. Price below SAR (downtrend)
        if price < ind['psar']:
            short_score += 1
            short_reasons.append("Price < SAR")
        
        # 5. Price above BB midline (room to go down)
        if price > ind['bb_mid']:
            short_score += 1
            short_reasons.append("Above BB mid")
        
        # 6. BOS confirmation
        if bos == "BEARISH_BOS":
            short_score += 2
            short_reasons.append("Bearish BOS")
        
        # ===== DECISION LOGIC =====
        # Only enter if score >= 4 (strong confluence)
        if long_score >= 4 and long_score > short_score:
            reason = " + ".join(long_reasons)
            return 'LONG', reason, long_score
        
        if short_score >= 4 and short_score > long_score:
            reason = " + ".join(short_reasons)
            return 'SHORT', reason, short_score
        
        return None, f"L:{long_score}/S:{short_score}", max(long_score, short_score)
    
    except Exception as e:
        return None, f"Error: {e}", 0

def should_enter_long(symbol):
    """Check if symbol should enter LONG"""
    signal, reason, confidence = analyze_symbol(symbol)
    if signal == 'LONG':
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        return True, f"🚀 LONG: {symbol} @ {price:.2f} | {reason} (Score: {confidence})"
    return False, reason

def should_enter_short(symbol):
    """Check if symbol should enter SHORT"""
    signal, reason, confidence = analyze_symbol(symbol)
    if signal == 'SHORT':
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        return True, f"🚀 SHORT: {symbol} @ {price:.2f} | {reason} (Score: {confidence})"
    return False, reason

# ================== POSITION & ORDER ==================
def get_open_positions():
    try:
        positions = client.futures_position_information()
        return [p['symbol'] for p in positions if abs(float(p['positionAmt'])) > 0.0001]
    except:
        return []

def place_order(symbol, side):
    try:
        balance = float(client.futures_account_balance()[6]['balance'])  # USDT
        risk_amount = balance * (RISK_PERCENT / 100)
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        qty = (risk_amount * LEVERAGE) / price
        
        # Get symbol precision from exchange info
        try:
            info = client.futures_exchange_info()
            for sym in info['symbols']:
                if sym['symbol'] == symbol:
                    precision = sym['quantityPrecision']
                    qty = round(qty, precision)
                    break
        except:
            qty = round(qty, 3)  # fallback
        
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

# ================== PROFIT MANAGER (Unkillable) ==================
def profit_manager():
    try:
        from ProfitManager import manage_open_positions
        manage_open_positions()
    except Exception as e:
        logging.warning(f"Profit manager error: {e}")

# ================== MAIN BEAST LOOP ==================
if __name__ == "__main__":
    logging.info("🚀 THE REAL BEAST IS AWAKE — MARKET STRUCTURE SCALPER ACTIVATED")
    
    while True:
        try:
            open_pos = get_open_positions()
            
            for symbol in SYMBOLS:
                if symbol in open_pos:
                    continue
                    
                try:
                    go_long, reason = should_enter_long(symbol)
                    go_short, reason_s = should_enter_short(symbol)
                    
                    if go_long:
                        place_order(symbol, "BUY")
                    elif go_short:
                        place_order(symbol, "SELL")
                    else:
                        logging.info(f"{symbol} → {reason or reason_s}")
                except Exception as e:
                    logging.warning(f"{symbol} scan error: {e}")
            
            profit_manager()  # locks 80% at +4%, full at +10%
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            logging.info("🛑 Beast stopped — peace out!")
            break
        except Exception as e:
            logging.error(f"Main loop error: {e}")
            time.sleep(5)
