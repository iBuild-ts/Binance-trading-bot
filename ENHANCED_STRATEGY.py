#!/usr/bin/env python3
"""
ENHANCED_STRATEGY.py
Professional-grade trading signals with multiple indicators
Combines momentum, trend, volatility, and volume analysis
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# ================== TECHNICAL INDICATORS ==================

def calculate_rsi(prices, period=14):
    """Calculate Relative Strength Index"""
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)
    
    for i in range(period, len(prices)):
        delta = deltas[i-1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
        
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)
    
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD (Moving Average Convergence Divergence)"""
    ema_fast = pd.Series(prices).ewm(span=fast).mean().values
    ema_slow = pd.Series(prices).ewm(span=slow).mean().values
    macd_line = ema_fast - ema_slow
    signal_line = pd.Series(macd_line).ewm(span=signal).mean().values
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    sma = pd.Series(prices).rolling(window=period).mean().values
    std = pd.Series(prices).rolling(window=std_dev).std().values
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    return upper_band, sma, lower_band

def calculate_atr(high, low, close, period=14):
    """Calculate Average True Range"""
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low - np.roll(close, 1))
        )
    )
    atr = pd.Series(tr).rolling(window=period).mean().values
    return atr

def calculate_adx(high, low, close, period=14):
    """Calculate Average Directional Index"""
    plus_dm = np.where(high - np.roll(high, 1) > np.roll(low, 1) - low, 
                       np.maximum(high - np.roll(high, 1), 0), 0)
    minus_dm = np.where(np.roll(low, 1) - low > high - np.roll(high, 1), 
                        np.maximum(np.roll(low, 1) - low, 0), 0)
    
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low - np.roll(close, 1))
        )
    )
    
    atr = pd.Series(tr).rolling(window=period).mean().values
    plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean().values / atr
    minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean().values / atr
    
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 0.001)
    adx = pd.Series(dx).rolling(window=period).mean().values
    
    return adx, plus_di, minus_di

def calculate_stochastic(high, low, close, period=14, smooth_k=3, smooth_d=3):
    """Calculate Stochastic Oscillator"""
    lowest_low = pd.Series(low).rolling(window=period).min().values
    highest_high = pd.Series(high).rolling(window=period).max().values
    
    k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low + 0.001)
    k_line = pd.Series(k_percent).rolling(window=smooth_k).mean().values
    d_line = pd.Series(k_line).rolling(window=smooth_d).mean().values
    
    return k_line, d_line

# ================== SIGNAL GENERATION ==================

def generate_long_signal(df, current_idx):
    """
    Generate LONG signal based on multiple indicators
    Returns: (signal_strength, reasons)
    """
    if current_idx < 50:
        return 0, []
    
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    volume = df['volume'].values
    
    reasons = []
    score = 0
    
    # 1. RSI Oversold (30-50 range is good for long)
    rsi = calculate_rsi(close, period=14)
    if 30 < rsi[current_idx] < 50:
        score += 20
        reasons.append(f"RSI={rsi[current_idx]:.1f} (oversold recovery)")
    
    # 2. MACD Bullish Crossover
    macd_line, signal_line, histogram = calculate_macd(close)
    if histogram[current_idx] > 0 and histogram[current_idx-1] <= 0:
        score += 25
        reasons.append("MACD bullish crossover")
    elif histogram[current_idx] > 0:
        score += 10
        reasons.append("MACD positive histogram")
    
    # 3. Price above SMA20 (uptrend)
    sma_20 = pd.Series(close).rolling(window=20).mean().values
    if close[current_idx] > sma_20[current_idx]:
        score += 15
        reasons.append(f"Price above SMA20 (trend)")
    
    # 4. Bollinger Band Squeeze (volatility expansion)
    upper_bb, middle_bb, lower_bb = calculate_bollinger_bands(close, period=20)
    bb_width = upper_bb[current_idx] - lower_bb[current_idx]
    bb_width_prev = upper_bb[current_idx-5] - lower_bb[current_idx-5]
    
    if bb_width > bb_width_prev and close[current_idx] > lower_bb[current_idx]:
        score += 15
        reasons.append("BB expanding upward")
    
    # 5. Volume Surge (above 20-period average)
    volume_ma = pd.Series(volume).rolling(window=20).mean().values
    if volume[current_idx] > volume_ma[current_idx] * 1.5:
        score += 15
        reasons.append(f"Volume surge ({volume[current_idx]/volume_ma[current_idx]:.1f}x)")
    
    # 6. ADX Trend Strength
    adx, plus_di, minus_di = calculate_adx(high, low, close)
    if adx[current_idx] > 25 and plus_di[current_idx] > minus_di[current_idx]:
        score += 10
        reasons.append(f"Strong uptrend (ADX={adx[current_idx]:.1f})")
    
    # 7. Stochastic Oversold
    k_line, d_line = calculate_stochastic(high, low, close)
    if k_line[current_idx] < 30 and k_line[current_idx] > k_line[current_idx-1]:
        score += 10
        reasons.append(f"Stochastic oversold recovery (K={k_line[current_idx]:.1f})")
    
    # Normalize score to 0-100
    signal_strength = min(score, 100)
    
    return signal_strength, reasons

def generate_short_signal(df, current_idx):
    """
    Generate SHORT signal based on multiple indicators
    Returns: (signal_strength, reasons)
    """
    if current_idx < 50:
        return 0, []
    
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    volume = df['volume'].values
    
    reasons = []
    score = 0
    
    # 1. RSI Overbought (50-70 range is good for short)
    rsi = calculate_rsi(close, period=14)
    if 50 < rsi[current_idx] < 70:
        score += 20
        reasons.append(f"RSI={rsi[current_idx]:.1f} (overbought reversal)")
    
    # 2. MACD Bearish Crossover
    macd_line, signal_line, histogram = calculate_macd(close)
    if histogram[current_idx] < 0 and histogram[current_idx-1] >= 0:
        score += 25
        reasons.append("MACD bearish crossover")
    elif histogram[current_idx] < 0:
        score += 10
        reasons.append("MACD negative histogram")
    
    # 3. Price below SMA20 (downtrend)
    sma_20 = pd.Series(close).rolling(window=20).mean().values
    if close[current_idx] < sma_20[current_idx]:
        score += 15
        reasons.append(f"Price below SMA20 (downtrend)")
    
    # 4. Bollinger Band Squeeze (volatility expansion downward)
    upper_bb, middle_bb, lower_bb = calculate_bollinger_bands(close, period=20)
    bb_width = upper_bb[current_idx] - lower_bb[current_idx]
    bb_width_prev = upper_bb[current_idx-5] - lower_bb[current_idx-5]
    
    if bb_width > bb_width_prev and close[current_idx] < upper_bb[current_idx]:
        score += 15
        reasons.append("BB expanding downward")
    
    # 5. Volume Surge (above 20-period average)
    volume_ma = pd.Series(volume).rolling(window=20).mean().values
    if volume[current_idx] > volume_ma[current_idx] * 1.5:
        score += 15
        reasons.append(f"Volume surge ({volume[current_idx]/volume_ma[current_idx]:.1f}x)")
    
    # 6. ADX Trend Strength
    adx, plus_di, minus_di = calculate_adx(high, low, close)
    if adx[current_idx] > 25 and minus_di[current_idx] > plus_di[current_idx]:
        score += 10
        reasons.append(f"Strong downtrend (ADX={adx[current_idx]:.1f})")
    
    # 7. Stochastic Overbought
    k_line, d_line = calculate_stochastic(high, low, close)
    if k_line[current_idx] > 70 and k_line[current_idx] < k_line[current_idx-1]:
        score += 10
        reasons.append(f"Stochastic overbought reversal (K={k_line[current_idx]:.1f})")
    
    # Normalize score to 0-100
    signal_strength = min(score, 100)
    
    return signal_strength, reasons

# ================== MAIN STRATEGY FUNCTION ==================

def enhanced_momentum_strategy(df, current_idx, symbol="BTCUSDT", min_signal_strength=50):
    """
    Main strategy function
    Returns: (direction, signal_strength, reasons)
    direction: 1 = LONG, -1 = SHORT, 0 = NO SIGNAL
    """
    
    if current_idx < 50:
        return 0, 0, ["Insufficient data"]
    
    long_strength, long_reasons = generate_long_signal(df, current_idx)
    short_strength, short_reasons = generate_short_signal(df, current_idx)
    
    # Determine direction based on strongest signal
    if long_strength > short_strength and long_strength >= min_signal_strength:
        return 1, long_strength, long_reasons
    elif short_strength > long_strength and short_strength >= min_signal_strength:
        return -1, short_strength, short_reasons
    else:
        return 0, max(long_strength, short_strength), ["Signal strength too low"]

# ================== RISK MANAGEMENT ==================

def calculate_position_size(account_balance, risk_percent, entry_price, stop_loss_price):
    """Calculate position size based on risk management"""
    risk_amount = account_balance * (risk_percent / 100)
    price_difference = abs(entry_price - stop_loss_price)
    
    if price_difference == 0:
        return 0
    
    position_size = risk_amount / price_difference
    return position_size

def calculate_take_profit(entry_price, direction, risk_reward_ratio=2.0, stop_loss_price=None):
    """Calculate take profit based on risk/reward ratio"""
    if stop_loss_price is None:
        # Default: 1% of entry price
        stop_loss_price = entry_price * 0.99 if direction == 1 else entry_price * 1.01
    
    risk = abs(entry_price - stop_loss_price)
    
    if direction == 1:  # LONG
        take_profit = entry_price + (risk * risk_reward_ratio)
    else:  # SHORT
        take_profit = entry_price - (risk * risk_reward_ratio)
    
    return take_profit

# ================== EXAMPLE USAGE ==================

if __name__ == "__main__":
    # Example: Create sample data
    import random
    
    dates = pd.date_range('2025-01-01', periods=100, freq='1H')
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices + np.random.randn(100) * 0.1,
        'high': prices + abs(np.random.randn(100) * 0.2),
        'low': prices - abs(np.random.randn(100) * 0.2),
        'close': prices,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # Test strategy on last candle
    current_idx = len(df) - 1
    direction, strength, reasons = enhanced_momentum_strategy(df, current_idx)
    
    print(f"\n{'='*60}")
    print(f"ENHANCED STRATEGY SIGNAL")
    print(f"{'='*60}")
    print(f"Direction: {'LONG' if direction == 1 else 'SHORT' if direction == -1 else 'NO SIGNAL'}")
    print(f"Signal Strength: {strength:.1f}%")
    print(f"Reasons:")
    for reason in reasons:
        print(f"  • {reason}")
    print(f"{'='*60}\n")
