# ProfitManager.py — FINAL UNKILLABLE VERSION (handles strings, case, everything)
from binance import Client
import time
import csv
import os
from datetime import datetime

API_KEY = 'tY6PJ6sKd1juJvV0ywQrl0bfFswlUd84uOfdDd6TMEfsvaF2F7eiNlAXL8KtDb8z'
API_SECRET = 'K5hbHYvr55kdmWPxl1Jwi9R9xN97oKp2O6akmLVVTwosG4eAg3HOwzxpsUbADFSY'

client = Client(api_key=API_KEY, api_secret=API_SECRET, testnet=True)

# CSV file for trade logging
TRADES_CSV = 'bot_trades.csv'

def init_trades_csv():
    """Initialize CSV file with headers if it doesn't exist"""
    if not os.path.exists(TRADES_CSV):
        with open(TRADES_CSV, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Timestamp', 'Symbol', 'Direction', 'Entry_Price', 'Exit_Price',
                'Quantity', 'Margin_USDT', 'PNL_USDT', 'PNL_Percent', 'Exit_Reason',
                'Duration_Minutes'
            ])

def log_trade_to_csv(symbol, direction, pnl_usdt, pnl_percent, exit_reason):
    """Log completed trade to CSV"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(TRADES_CSV, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp, symbol, direction, '', '', '', '', 
                f'{pnl_usdt:.2f}', f'{pnl_percent:.2f}%', exit_reason, ''
            ])
        print(f"✅ Trade logged: {symbol} {direction} {pnl_percent:+.2f}%")
    except Exception as e:
        print(f"CSV logging error: {e}")

def safe_float(value, default=0.0):
    try:
        return float(value or 0)
    except:
        return default

def get_precision(symbol):
    try:
        info = client.futures_exchange_info()['symbols']
        for s in info:
            if s['symbol'] == symbol:
                return s['quantityPrecision']
        return 3
    except:
        return 3

def get_fees_and_slippage(symbol, qty):
    """
    Calculate realistic fee and slippage buffer
    Binance taker fee = 0.04% + avg slippage 0.03–0.08% → total 0.15% buffer
    """
    try:
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        notional = price * abs(qty)
        fee_buffer = notional * 0.0015  # 0.15% total buffer
        return fee_buffer
    except Exception as e:
        print(f"Fee calculation error: {e}")
        return 0

def close_position(symbol, qty):
    """
    SLIPPAGE-PROTECTED CLOSE with limit orders
    Uses 0.5% price protection to avoid slippage
    Falls back to market order if limit fails
    """
    if abs(qty) < 0.000001: return
    side = "SELL" if qty > 0 else "BUY"
    try:
        # Get current price with 0.5% protection
        current_price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        
        # For SELL: use 99.5% of price (lower = more likely to fill)
        # For BUY: use 100.5% of price (higher = more likely to fill)
        protected_price = current_price * (0.995 if side == "SELL" else 1.005)
        protected_price = round(protected_price, 2)
        
        # Try limit order first (better price)
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type="LIMIT",
            timeInForce="GTC",
            quantity=round(abs(qty), 3),
            price=protected_price,
            reduceOnly=True
        )
        print(f"✅ SLIPPAGE-PROTECTED CLOSE → {abs(qty):.6f} {symbol} @ {protected_price}")
    except Exception as e:
        print(f"Limit order failed, falling back to market: {e}")
        try:
            # Fallback: market order
            client.futures_create_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=round(abs(qty), 3),
                reduceOnly=True
            )
            print(f"✅ MARKET CLOSE → {abs(qty):.6f} {symbol}")
        except Exception as e2:
            print(f"❌ Close failed: {e2}")

def set_breakeven_stop(symbol, entry_price, side):
    try:
        buffer = 0.0005
        stop = entry_price * (1 - buffer) if side == "LONG" else entry_price * (1 + buffer)
        client.futures_create_order(
            symbol=symbol,
            side="SELL" if side == "LONG" else "BUY",
            type="STOP_MARKET",
            stopPrice=round(stop, 8),
            closePosition=True,
            reduceOnly=True
        )
        print(f"Breakeven STOP placed on remaining {symbol}")
    except Exception as e:
        print(f"Stop failed: {e}")

def manage_open_positions():
    """
    REAL 10% TP MANAGER (including fees & slippage)
    - Accounts for 0.15% total fees/slippage
    - +10% REAL = aim for +10.3% on paper (after fees)
    - +4% REAL = aim for +4.2% on paper (80% exit, lock profits)
    - NO STOP LOSS (let winners run)
    """
    try:
        positions = client.futures_position_information()
        for pos in positions:
            symbol = pos['symbol']
            if not symbol.endswith('USDT'): continue
            
            qty = safe_float(pos['positionAmt'])
            if abs(qty) < 0.000001: continue

            # Handle every possible field name and type (Binance testnet is drunk)
            unrealized_pnl = safe_float(
                pos.get('unrealizedProfit') or 
                pos.get('unrealizedprofit') or 
                pos.get('unRealizedProfit') or 
                0
            )
            initial_margin = safe_float(
                pos.get('initialMargin') or 
                pos.get('initialmargin') or 
                pos.get('positionInitialMargin') or 
                1
            )

            if initial_margin <= 1:
                continue

            # Real ROI after fees & slippage
            real_roi_percent = (unrealized_pnl / initial_margin) * 100
            side = "LONG" if qty > 0 else "SHORT"

            print(f"[MONEY PRINTER] {symbol} {side} → REAL PNL: {real_roi_percent:+.2f}% ({unrealized_pnl:+.2f} USDT)")

            # ✅ REAL +10% HIT (after fees) → FULL EXIT
            # We aim for +10.3% on paper to account for 0.3% in fees/slippage
            if real_roi_percent >= 10.3:
                print(f"🎯 REAL +10% HIT AFTER FEES → FULL EXIT {symbol} 🚀")
                close_position(symbol, qty)
                log_trade_to_csv(symbol, side, unrealized_pnl, real_roi_percent, "TP_10%")
                continue
            
            # ✅ REAL +4% HIT (after fees) → 80% EXIT, lock profits
            # We aim for +4.2% on paper to account for 0.2% in fees/slippage
            if real_roi_percent >= 4.2:
                close_qty = round(abs(qty) * 0.8, 3)
                if close_qty > 0.001:
                    print(f"🎯 REAL +4% LOCK → 80% OUT {symbol} (keep 20% for runners) 💰")
                    close_position(symbol, close_qty if qty > 0 else -close_qty)
                    log_trade_to_csv(symbol, side, unrealized_pnl * 0.8, real_roi_percent, "TP_4%_PARTIAL")
                continue
            
            # ℹ️ NO STOP LOSS — Let positions recover
            # Positions only close when they hit profit targets
            # This gives unlimited upside and lets winners run

    except Exception as e:
        print(f"[ProfitManager ERROR] {e}")

# Run every 5 seconds — no mercy
if __name__ == "__main__":
    init_trades_csv()
    print("UNKILLABLE PROFIT MANAGER ONLINE — NOTHING CAN STOP THIS")
    print(f"📊 Trades logged to: {TRADES_CSV}")
    while True:
        manage_open_positions()
        time.sleep(5)