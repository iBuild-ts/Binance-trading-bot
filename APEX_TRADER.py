# ===================================================
# APEX_TRADER.py — THE FINAL WEAPON (2025 Elite Edition)
# PROJECT APEX: BTC | ETH | BNB only | 40-50% daily target
# ANTI-DEGEN HARDENED | FULL FORENSIC REASONING
# ===================================================

import time
import pandas as pd
import numpy as np
from binance import Client
import requests
import json
from datetime import datetime
import logging
import os
from urllib3.exceptions import MaxRetryError, NameResolutionError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ================== ANTI-DEGEN IMPORTS ==================
from NewsFilter import should_pause_trading
from DailyLimits import DailyLimitsManager
from ProfitManager import manage_open_positions

# ================== CONFIG ==================
API_KEY = os.getenv('BINANCE_API_KEY', '')
API_SECRET = os.getenv('BINANCE_API_SECRET', '')

if not API_KEY or not API_SECRET:
    raise ValueError("❌ CRITICAL: API keys not found in .env file. Create .env with BINANCE_API_KEY and BINANCE_API_SECRET")

client = Client(api_key=API_KEY, api_secret=API_SECRET, testnet=True)

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
LEVERAGE_RANGE = (8, 25)  # Dynamic leverage based on conviction
RISK_PER_TRADE = 0.02     # 2% base, scales with conviction
MAX_TRADES_PER_DAY = 8
CONVICTION_THRESHOLD = 0.91

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)

# ================== STATE TRACKING ==================
state = {
    "trades_today": 0,
    "daily_pnl": 0.0,
    "last_reset": datetime.now().date(),
    "active_trades": {},
    "connection_failures": 0
}

# ================== RETRY LOGIC WITH EXPONENTIAL BACKOFF ==================
def retry_with_backoff(func, max_retries=3, base_delay=1):
    """
    Retry function with exponential backoff
    Handles connection errors gracefully
    """
    for attempt in range(max_retries):
        try:
            return func()
        except (MaxRetryError, NameResolutionError, requests.ConnectionError, 
                ConnectionError, TimeoutError, Exception) as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logging.warning(f"Connection error (attempt {attempt + 1}/{max_retries}), retrying in {delay}s: {type(e).__name__}")
                time.sleep(delay)
                state["connection_failures"] += 1
            else:
                logging.error(f"Max retries exceeded: {e}")
                return None
    return None

# ================== APEX TRADE LOG ==================
APEX_LOG_FILE = 'apex_trades.csv'

def init_apex_log():
    """Initialize trade log with headers"""
    if not os.path.exists(APEX_LOG_FILE):
        with open(APEX_LOG_FILE, 'w') as f:
            f.write('Timestamp,Symbol,Direction,Conviction,Leverage,Risk_USD,Entry_Price,Reasons,Status\n')

def log_apex_trade(symbol, direction, conviction, leverage, risk, price, reasons):
    """Log trade with full forensic details"""
    with open(APEX_LOG_FILE, 'a') as f:
        reason_str = '|'.join(reasons)
        f.write(f'{datetime.now().isoformat()},{symbol},{direction},{conviction:.3f},{leverage},{risk:.2f},{price:.2f},"{reason_str}",EXECUTED\n')

# ================== NEWS & SENTIMENT KILL SWITCH ==================
def high_impact_news_block():
    """
    APEX NEWS BLOCKER — Detects market-moving events
    Monitors: FOMC, Fed, CPI, PPI, SEC, hacks, exploits, liquidations
    """
    try:
        # CryptoPanic API
        r = requests.get(
            "https://api.cryptopanic.com/v1/posts/?auth_token=PUBLIC&kind=news&filter=hot",
            timeout=5
        )
        posts = r.json()['results'][:10]
        titles = " ".join([p['title'].lower() for p in posts])
        
        # Kill words that trigger pause
        kill_words = [
            'fed', 'fomc', 'cpi', 'ppi', 'sec approves', 'sec rejects',
            'binance', 'hack', 'liquidation cascade', 'etf decision',
            'emergency', 'crisis', 'circuit breaker', 'halt', 'suspend',
            'exploit', 'breach', 'bankruptcy', 'collapse'
        ]
        
        if any(word in titles for word in kill_words):
            return True, f"🚨 HIGH IMPACT NEWS DETECTED — APEX PAUSED"
    except:
        pass
    
    return False, "✅ Market clear"

# ================== DEEP MULTI-TIMEFRAME ANALYSIS ENGINE ==================
def apex_analysis(symbol):
    """
    APEX ANALYSIS ENGINE
    Multi-timeframe confluence detection with full forensic reasoning
    """
    try:
        # Fetch multi-timeframe data with retry logic
        def fetch_4h():
            return pd.DataFrame(client.futures_klines(symbol=symbol, interval='4h', limit=100))
        
        def fetch_15m():
            return pd.DataFrame(client.futures_klines(symbol=symbol, interval='15m', limit=200))
        
        df_4h = retry_with_backoff(fetch_4h, max_retries=3, base_delay=1)
        df_15m = retry_with_backoff(fetch_15m, max_retries=3, base_delay=1)
        
        if df_4h is None or df_15m is None or df_4h.empty or df_15m.empty:
            return None
        
        # Rename columns for clarity
        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_vol', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore']
        df_4h.columns = columns
        df_15m.columns = columns
        
        # Convert to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_4h[col] = pd.to_numeric(df_4h[col], errors='coerce')
            df_15m[col] = pd.to_numeric(df_15m[col], errors='coerce')
        
        # Get current price with retry logic
        def fetch_price():
            return float(client.futures_symbol_ticker(symbol=symbol)['price'])
        
        price = retry_with_backoff(fetch_price, max_retries=3, base_delay=1)
        if price is None:
            return None
        
        # ========== 4H BIAS (Macro Direction) ==========
        ema50_4h = df_4h['close'].rolling(50).mean().iloc[-1]
        ema200_4h = df_4h['close'].rolling(200).mean().iloc[-1]
        bias = "BULLISH" if ema50_4h > ema200_4h else "BEARISH"
        
        # ========== BREAK OF STRUCTURE (15m) ==========
        recent_high = df_15m['high'].iloc[-20:].max()
        recent_low = df_15m['low'].iloc[-20:].min()
        bos_bull = price > recent_high and df_15m['high'].iloc[-1] > recent_high
        bos_bear = price < recent_low and df_15m['low'].iloc[-1] < recent_low
        
        # ========== ORDER BLOCK DETECTION ==========
        ob_zone = None
        for i in range(-15, -3):
            if bos_bull and df_15m['close'].iloc[i] < df_15m['open'].iloc[i]:  # Bear candle
                ob_zone = (df_15m['low'].iloc[i], df_15m['high'].iloc[i])
                break
            if bos_bear and df_15m['close'].iloc[i] > df_15m['open'].iloc[i]:  # Bull candle
                ob_zone = (df_15m['low'].iloc[i], df_15m['high'].iloc[i])
                break
        
        # ========== VOLUME ANALYSIS ==========
        vol_avg = df_15m['volume'].iloc[-20:].mean()
        vol_now = df_15m['volume'].iloc[-1]
        vol_spike = vol_now > vol_avg * 2.5
        vol_increase_pct = ((vol_now - vol_avg) / vol_avg * 100) if vol_avg > 0 else 0
        
        # ========== CONFLUENCE SCORING (SIMPLIFIED FOR TESTNET) ==========
        score = 0.0
        reasons = []
        confluence_count = 0
        
        # Macro bias (40% weight)
        if bias == "BULLISH":
            score += 0.40
            confluence_count += 1
            reasons.append("4h BULLISH bias (EMA50 > EMA200)")
        elif bias == "BEARISH":
            score -= 0.40
            confluence_count += 1
            reasons.append("4h BEARISH bias (EMA50 < EMA200)")
        
        # Break of Structure (30% weight)
        if bos_bull:
            score += 0.30
            confluence_count += 1
            reasons.append("Bullish BOS confirmed (new 20-candle high)")
        elif bos_bear:
            score -= 0.30
            confluence_count += 1
            reasons.append("Bearish BOS confirmed (new 20-candle low)")
        
        # Order Block (20% weight) - RELAXED ZONE
        if ob_zone and ob_zone[0] <= price <= ob_zone[1] * 1.02:  # Increased from 1.008 to 1.02
            score += 0.20
            confluence_count += 1
            reasons.append(f"Price in Order Block zone {ob_zone[0]:.2f}-{ob_zone[1]:.2f}")
        
        # Volume Spike (10% weight) - RELAXED THRESHOLD
        if vol_spike or vol_increase_pct > 150:  # Added alternative: 150% volume increase
            score += 0.10
            confluence_count += 1
            reasons.append(f"Volume spike +{vol_increase_pct:.0f}% (avg {vol_avg:.0f} → now {vol_now:.0f})")
        
        # SIMPLIFIED ENTRY: Only need 1 confluence factor + bias
        direction = "LONG" if score > 0 else "SHORT" if score < 0 else "NONE"
        conviction = min(abs(score), 1.0)
        
        # NEW: Lower threshold for testnet (0.40 instead of 0.91)
        # This allows trading with just bias + 1 other factor
        # Conviction 0.40 = bias (0.40) alone
        # Conviction 0.70 = bias (0.40) + order block (0.20) + volume (0.10)
        
        return {
            "symbol": symbol,
            "direction": direction,
            "conviction": conviction,
            "price": price,
            "reasons": reasons,
            "bias": bias,
            "bos_bull": bos_bull,
            "bos_bear": bos_bear,
            "ob_zone": ob_zone,
            "vol_spike": vol_spike,
            "vol_increase": vol_increase_pct
        }
    
    except Exception as e:
        logging.error(f"Analysis error for {symbol}: {e}")
        return None

# ================== EXECUTION WITH FULL FORENSIC EXPLANATION ==================
def execute_trade(analysis):
    """
    APEX EXECUTION ENGINE
    Executes trade with full forensic reasoning and anti-degen checks
    """
    if state["trades_today"] >= MAX_TRADES_PER_DAY:
        logging.warning(f"[DAILY LIMIT] {state['trades_today']}/{MAX_TRADES_PER_DAY} trades reached")
        return
    
    symbol = analysis["symbol"]
    direction = analysis["direction"]
    conviction = analysis["conviction"]
    
    # TESTNET MODE: Lower threshold to 0.40 (bias alone is enough)
    # LIVE MODE: Use 0.91 (strict confluence required)
    testnet_threshold = 0.40
    
    if conviction < testnet_threshold:
        logging.debug(f"{symbol} conviction {conviction:.3f} < threshold {testnet_threshold}")
        return
    
    # ========== DYNAMIC LEVERAGE CALCULATION ==========
    # Base 8x, scales to 25x with conviction
    # For testnet: conviction 0.40-1.00 maps to leverage 8-25x
    conviction_factor = (conviction - 0.40) / (1.0 - 0.40)  # Normalize to 0-1 range
    conviction_factor = max(0, min(1, conviction_factor))  # Clamp to 0-1
    lev = int(LEVERAGE_RANGE[0] + (LEVERAGE_RANGE[1] - LEVERAGE_RANGE[0]) * conviction_factor)
    lev = max(LEVERAGE_RANGE[0], min(LEVERAGE_RANGE[1], lev))
    
    # ========== POSITION SIZING ==========
    try:
        balance = float(client.futures_account_balance()[6]['balance'])
        risk_amount = balance * RISK_PER_TRADE * (conviction * 1.5)
        qty = round((risk_amount * lev) / analysis["price"], 3)
        
        side = "BUY" if direction == "LONG" else "SELL"
        
        # ========== EXECUTE ORDER ==========
        client.futures_change_leverage(symbol=symbol, leverage=lev)
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=qty
        )
        
        # ========== FORENSIC EXPLANATION ==========
        explanation = f"""
╔════════════════════════════════════════════════════════════════════════════╗
║                         🎯 APEX EXECUTION REPORT                          ║
╚════════════════════════════════════════════════════════════════════════════╝

TRADE: {symbol} {direction}
Conviction: {conviction:.3f}/1.00 | Leverage: {lev}x | Risk: ${risk_amount:.1f}
Entry Price: {analysis['price']:.2f} | Quantity: {qty}

CONFLUENCE ANALYSIS:
  • Macro Bias: {analysis['bias']}
  • BOS Bull: {'✅ YES' if analysis['bos_bull'] else '❌ NO'}
  • BOS Bear: {'✅ YES' if analysis['bos_bear'] else '❌ NO'}
  • Order Block: {'✅ IN ZONE' if analysis['ob_zone'] else '❌ OUTSIDE'}
  • Volume Spike: {'✅ YES (+{:.0f}%)' if analysis['vol_spike'] else '❌ NO'} {analysis['vol_increase']:.0f}%

REASONS FOR ENTRY:
"""
        for i, reason in enumerate(analysis['reasons'], 1):
            explanation += f"  {i}. {reason}\n"
        
        explanation += f"""
TRADE MANAGEMENT:
  • Stop Loss: NONE (let winners run)
  • Take Profit: Real +10% (after fees)
  • Partial Exit: +4% (80% close, 20% runner)
  • Slippage Protection: 0.5% buffer on exits

Status: ✅ EXECUTED | Order ID: {order.get('orderId', 'N/A')}
╚════════════════════════════════════════════════════════════════════════════╝
"""
        
        logging.info(explanation)
        log_apex_trade(symbol, direction, conviction, lev, risk_amount, analysis['price'], analysis['reasons'])
        state["trades_today"] += 1
        state["active_trades"][symbol] = {
            "direction": direction,
            "entry_price": analysis['price'],
            "conviction": conviction
        }
    
    except Exception as e:
        logging.error(f"❌ Execution failed for {symbol}: {e}")

# ================== MAIN APEX LOOP WITH ANTI-DEGEN ==================
if __name__ == "__main__":
    logging.info("╔════════════════════════════════════════════════════════════════════════════╗")
    logging.info("║                     🚀 PROJECT APEX ONLINE 🚀                             ║")
    logging.info("║              3 PAIRS | 3-8 TRADES/DAY | 40-50% DAILY TARGET              ║")
    logging.info("║         ANTI-DEGEN HARDENED | NEWS FILTER | DAILY LIMITS | SLIPPAGE      ║")
    logging.info("╚════════════════════════════════════════════════════════════════════════════╝")
    
    init_apex_log()
    
    # Initialize anti-degen components
    daily_limits = DailyLimitsManager(API_KEY, API_SECRET, testnet=True)
    
    last_analysis_time = 0
    analysis_interval = 180  # Deep analysis every 3 minutes
    
    while True:
        try:
            # ========== RESET DAILY STATE ==========
            if datetime.now().date() != state["last_reset"]:
                state["trades_today"] = 0
                state["daily_pnl"] = 0.0
                state["last_reset"] = datetime.now().date()
                logging.info("📅 Daily reset — new trading session started")
            
            # ========== ANTI-DEGEN CHECK 1: NEWS FILTER ==========
            try:
                news_block, news_msg = high_impact_news_block()
                if news_block:
                    logging.warning(news_msg)
                    time.sleep(300)  # Wait 5 minutes
                    continue
            except Exception as e:
                logging.warning(f"News filter error (continuing): {type(e).__name__}")
            
            # ========== ANTI-DEGEN CHECK 2: DAILY LIMITS ==========
            try:
                should_pause_limits, limits_reason = daily_limits.check_daily_limits()
                if should_pause_limits:
                    logging.warning(f"[DAILY LIMITS] {limits_reason}")
                    time.sleep(60)  # Wait 1 minute
                    continue
            except Exception as e:
                logging.warning(f"Daily limits error (continuing): {type(e).__name__}")
            
            # ========== ANTI-DEGEN CHECK 3: MANAGE PROFITS ==========
            try:
                manage_open_positions()
            except Exception as e:
                logging.warning(f"Profit manager error (continuing): {type(e).__name__}")
            
            # ========== APEX ANALYSIS LOOP ==========
            current_time = time.time()
            if current_time - last_analysis_time >= analysis_interval:
                logging.info(f"🔍 APEX ANALYSIS CYCLE | Trades: {state['trades_today']}/{MAX_TRADES_PER_DAY} | Connection failures: {state['connection_failures']}")
                
                for symbol in SYMBOLS:
                    try:
                        analysis = apex_analysis(symbol)
                        if analysis and analysis["direction"] != "NONE":
                            logging.info(
                                f"📊 {symbol} → {analysis['direction']} "
                                f"| Conviction: {analysis['conviction']:.3f} "
                                f"| Bias: {analysis['bias']}"
                            )
                            execute_trade(analysis)
                        else:
                            logging.debug(f"⏭️  {symbol} | No confluence signal")
                    except Exception as e:
                        logging.error(f"Error analyzing {symbol}: {type(e).__name__}: {str(e)[:100]}")
                
                last_analysis_time = current_time
            
            time.sleep(30)  # Check every 30 seconds
        
        except KeyboardInterrupt:
            logging.info("🛑 PROJECT APEX SHUTDOWN — Final status:")
            logging.info(f"   Trades executed: {state['trades_today']}")
            logging.info(f"   Daily PnL: {state['daily_pnl']:+.2f}%")
            logging.info(f"   See apex_trades.csv for full forensic log")
            break
        
        except Exception as e:
            logging.error(f"Main loop error: {e}")
            time.sleep(5)
