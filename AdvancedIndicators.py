"""
ADVANCED TRADING INDICATORS — PREMIUM EFFICIENCY FILTERS
- Trend Bias (EMA50/EMA200)
- Break of Structure (BOS) / Change of Character (CHOCH)
- Order Block Detection (Demand/Supply Zones)
- Volume Profile & Liquidity Zones
- Volatility Filters (ATR-based)
- Momentum Divergence Detection
- Multi-timeframe confluence
"""

import pandas as pd
import ta
import numpy as np
from Logger import *


def get_trend_bias(df):
    """
    Analyze trend using EMA50 and EMA200
    Returns: "BULLISH_REVERSAL", "BEARISH_REVERSAL", "BULLISH", "BEARISH", or "SIDEWAYS"
    """
    try:
        if len(df) < 200:
            return "INSUFFICIENT_DATA"
        
        close_series = pd.Series(df['close'].values)
        
        # Calculate EMAs
        ema50 = ta.trend.EMAIndicator(close_series, window=50).ema_indicator()
        ema200 = ta.trend.EMAIndicator(close_series, window=200).ema_indicator()
        
        last_ema50 = ema50.iloc[-1]
        last_ema200 = ema200.iloc[-1]
        prev_ema50 = ema50.iloc[-2]
        prev_ema200 = ema200.iloc[-2]
        
        # Detect reversals (crossovers)
        if last_ema50 > last_ema200 and prev_ema50 <= prev_ema200:
            return "BULLISH_REVERSAL"
        elif last_ema50 < last_ema200 and prev_ema50 >= prev_ema200:
            return "BEARISH_REVERSAL"
        elif last_ema50 > last_ema200:
            return "BULLISH"
        elif last_ema50 < last_ema200:
            return "BEARISH"
        else:
            return "SIDEWAYS"
    except Exception as e:
        log.warning(f"get_trend_bias() error: {e}")
        return "ERROR"


def detect_bos(df):
    """
    Detect Break of Structure (BOS) / Change of Character (CHOCH)
    Returns: "BULLISH_BOS", "BEARISH_BOS", or None
    """
    try:
        if len(df) < 25:
            return None
        
        highs = df['high'].rolling(window=20).max()
        lows = df['low'].rolling(window=20).min()
        
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        prev_high = highs.iloc[-2]
        prev_low = lows.iloc[-2]
        
        # Bullish BOS: price breaks above previous 20-candle high
        if current_high > prev_high:
            return "BULLISH_BOS"
        
        # Bearish BOS: price breaks below previous 20-candle low
        if current_low < prev_low:
            return "BEARISH_BOS"
        
        return None
    except Exception as e:
        log.warning(f"detect_bos() error: {e}")
        return None


def find_order_block(df, direction="bullish"):
    """
    Find the last demand (bullish) or supply (bearish) zone
    Returns: (low_zone, high_zone) or (None, None)
    """
    try:
        if len(df) < 15:
            return None, None
        
        # Scan backwards from current candle
        for i in range(len(df) - 10, 10, -1):
            if direction == "bullish":
                # Look for a strong bearish candle (low < previous low)
                if df['low'].iloc[i - 1] > df['low'].iloc[i] < df['low'].iloc[i + 1]:
                    # Then check if it was engulfed (bullish candle after)
                    if df['close'].iloc[i + 1] > df['high'].iloc[i]:
                        return df['low'].iloc[i], df['high'].iloc[i]
            else:  # bearish
                # Look for a strong bullish candle (high > previous high)
                if df['high'].iloc[i - 1] < df['high'].iloc[i] > df['high'].iloc[i + 1]:
                    # Then check if it was engulfed (bearish candle after)
                    if df['close'].iloc[i + 1] < df['low'].iloc[i]:
                        return df['low'].iloc[i], df['high'].iloc[i]
        
        return None, None
    except Exception as e:
        log.warning(f"find_order_block() error: {e}")
        return None, None


def get_macd_signal(df):
    """
    Get MACD histogram signal
    Returns: "BULLISH", "BEARISH", or "NEUTRAL"
    """
    try:
        if len(df) < 26:
            return "NEUTRAL"
        
        close_series = pd.Series(df['close'].values)
        macd = ta.trend.MACD(close_series)
        
        macd_line = macd.macd()
        signal_line = macd.macd_signal()
        histogram = macd.macd_diff()
        
        last_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]
        
        # Bullish: histogram crosses above zero or is positive and increasing
        if last_hist > 0 and prev_hist <= 0:
            return "BULLISH"
        # Bearish: histogram crosses below zero or is negative and decreasing
        elif last_hist < 0 and prev_hist >= 0:
            return "BEARISH"
        elif last_hist > 0:
            return "BULLISH"
        elif last_hist < 0:
            return "BEARISH"
        else:
            return "NEUTRAL"
    except Exception as e:
        log.warning(f"get_macd_signal() error: {e}")
        return "NEUTRAL"


def get_rsi_signal(df, period=14):
    """
    Get RSI signal
    Returns: "OVERSOLD", "OVERBOUGHT", or "NEUTRAL"
    """
    try:
        if len(df) < period:
            return "NEUTRAL"
        
        close_series = pd.Series(df['close'].values)
        rsi = ta.momentum.RSIIndicator(close_series, window=period).rsi()
        
        last_rsi = rsi.iloc[-1]
        
        if last_rsi < 30:
            return "OVERSOLD"
        elif last_rsi > 70:
            return "OVERBOUGHT"
        else:
            return "NEUTRAL"
    except Exception as e:
        log.warning(f"get_rsi_signal() error: {e}")
        return "NEUTRAL"


def get_confluence_score(df, direction="long"):
    """
    Calculate confluence score (0-5) based on multiple indicators
    Higher score = stronger signal
    """
    try:
        score = 0
        
        # Trend bias (0-2 points)
        trend = get_trend_bias(df)
        if direction == "long" and "BULLISH" in trend:
            score += 2
        elif direction == "short" and "BEARISH" in trend:
            score += 2
        
        # BOS confirmation (0-1 point)
        bos = detect_bos(df)
        if direction == "long" and bos == "BULLISH_BOS":
            score += 1
        elif direction == "short" and bos == "BEARISH_BOS":
            score += 1
        
        # MACD confirmation (0-1 point)
        macd = get_macd_signal(df)
        if direction == "long" and macd == "BULLISH":
            score += 1
        elif direction == "short" and macd == "BEARISH":
            score += 1
        
        # RSI confirmation (0-1 point)
        rsi = get_rsi_signal(df)
        if direction == "long" and rsi == "OVERSOLD":
            score += 1
        elif direction == "short" and rsi == "OVERBOUGHT":
            score += 1
        
        return score
    except Exception as e:
        log.warning(f"get_confluence_score() error: {e}")
        return 0


def get_atr_volatility(df, period=14):
    """
    Calculate ATR and volatility ratio
    Returns: (atr_value, volatility_level)
    volatility_level: "LOW", "MEDIUM", "HIGH"
    """
    try:
        if len(df) < period:
            return 0, "INSUFFICIENT"
        
        high = pd.Series(df['high'].values)
        low = pd.Series(df['low'].values)
        close = pd.Series(df['close'].values)
        
        atr = ta.volatility.AverageTrueRange(high, low, close, window=period).average_true_range()
        atr_val = atr.iloc[-1]
        
        # Calculate volatility as % of price
        current_price = close.iloc[-1]
        volatility_pct = (atr_val / current_price) * 100
        
        if volatility_pct < 0.5:
            return atr_val, "LOW"
        elif volatility_pct < 1.5:
            return atr_val, "MEDIUM"
        else:
            return atr_val, "HIGH"
    except Exception as e:
        log.warning(f"get_atr_volatility() error: {e}")
        return 0, "ERROR"


def detect_volume_spike(df, period=20, threshold=1.5):
    """
    Detect abnormal volume spikes (liquidity confirmation)
    Returns: True if volume spike detected, False otherwise
    """
    try:
        if len(df) < period:
            return False
        
        volume = pd.Series(df['volume'].values)
        avg_volume = volume.rolling(window=period).mean()
        
        current_vol = volume.iloc[-1]
        avg_vol = avg_volume.iloc[-1]
        
        # Volume spike if current > threshold * average
        return current_vol > (avg_vol * threshold)
    except Exception as e:
        log.warning(f"detect_volume_spike() error: {e}")
        return False


def detect_momentum_divergence(df):
    """
    Detect RSI divergence (potential reversal signal)
    Returns: "BULLISH_DIV", "BEARISH_DIV", or None
    """
    try:
        if len(df) < 30:
            return None
        
        close = pd.Series(df['close'].values)
        rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
        
        # Look for last 10 candles
        recent_closes = close.iloc[-10:]
        recent_rsi = rsi.iloc[-10:]
        
        # Bullish divergence: price makes lower low, RSI makes higher low
        if recent_closes.iloc[-1] < recent_closes.iloc[-5]:
            if recent_rsi.iloc[-1] > recent_rsi.iloc[-5]:
                return "BULLISH_DIV"
        
        # Bearish divergence: price makes higher high, RSI makes lower high
        if recent_closes.iloc[-1] > recent_closes.iloc[-5]:
            if recent_rsi.iloc[-1] < recent_rsi.iloc[-5]:
                return "BEARISH_DIV"
        
        return None
    except Exception as e:
        log.warning(f"detect_momentum_divergence() error: {e}")
        return None


def get_support_resistance_levels(df, lookback=50):
    """
    Find recent support and resistance levels
    Returns: (support_level, resistance_level)
    """
    try:
        if len(df) < lookback:
            return None, None
        
        recent_high = df['high'].iloc[-lookback:].max()
        recent_low = df['low'].iloc[-lookback:].min()
        
        return recent_low, recent_high
    except Exception as e:
        log.warning(f"get_support_resistance_levels() error: {e}")
        return None, None


def is_price_at_key_level(price, support, resistance, tolerance=0.002):
    """
    Check if price is near support/resistance (within tolerance %)
    Returns: "AT_SUPPORT", "AT_RESISTANCE", or None
    """
    try:
        if support and abs(price - support) / support < tolerance:
            return "AT_SUPPORT"
        if resistance and abs(price - resistance) / resistance < tolerance:
            return "AT_RESISTANCE"
        return None
    except Exception as e:
        log.warning(f"is_price_at_key_level() error: {e}")
        return None


def get_stochastic_signal(df, period=14):
    """
    Get Stochastic oscillator signal
    Returns: "OVERSOLD", "OVERBOUGHT", or "NEUTRAL"
    """
    try:
        if len(df) < period:
            return "NEUTRAL"
        
        high = pd.Series(df['high'].values)
        low = pd.Series(df['low'].values)
        close = pd.Series(df['close'].values)
        
        stoch = ta.momentum.StochasticOscillator(high, low, close, window=period)
        stoch_k = stoch.stoch()
        
        last_k = stoch_k.iloc[-1]
        
        if last_k < 20:
            return "OVERSOLD"
        elif last_k > 80:
            return "OVERBOUGHT"
        else:
            return "NEUTRAL"
    except Exception as e:
        log.warning(f"get_stochastic_signal() error: {e}")
        return "NEUTRAL"


def get_premium_confluence_score(df, direction="long"):
    """
    PREMIUM SCORING SYSTEM (0-10 points)
    Combines all indicators for maximum accuracy
    """
    try:
        score = 0
        
        # Base confluence (0-5 points)
        base_score = get_confluence_score(df, direction)
        score += base_score
        
        # Volume spike confirmation (0-1 point)
        if detect_volume_spike(df):
            score += 1
        
        # Volatility filter (0-1 point) — only trade in MEDIUM-HIGH volatility
        atr, vol_level = get_atr_volatility(df)
        if vol_level in ["MEDIUM", "HIGH"]:
            score += 1
        
        # Momentum divergence bonus (0-1 point)
        div = detect_momentum_divergence(df)
        if direction == "long" and div == "BULLISH_DIV":
            score += 1
        elif direction == "short" and div == "BEARISH_DIV":
            score += 1
        
        # Stochastic confirmation (0-1 point)
        stoch = get_stochastic_signal(df)
        if direction == "long" and stoch == "OVERSOLD":
            score += 1
        elif direction == "short" and stoch == "OVERBOUGHT":
            score += 1
        
        # Support/Resistance confirmation (0-1 point)
        support, resistance = get_support_resistance_levels(df)
        price = df['close'].iloc[-1]
        key_level = is_price_at_key_level(price, support, resistance)
        if direction == "long" and key_level == "AT_SUPPORT":
            score += 1
        elif direction == "short" and key_level == "AT_RESISTANCE":
            score += 1
        
        return score
    except Exception as e:
        log.warning(f"get_premium_confluence_score() error: {e}")
        return 0
