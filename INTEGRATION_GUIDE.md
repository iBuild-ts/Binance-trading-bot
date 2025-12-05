# Integration Guide: Anti-Degen Trading System

This guide shows how to integrate the new anti-degen modules into your main trading loop.

## New Modules Created

1. **ProfitManager.py** (Updated)
   - Slippage-protected limit orders
   - Real 10% TP (accounts for 0.15% fees/slippage)
   - Real 4% partial exit (80% close, 20% runner)
   - No stop loss (let winners run)

2. **NewsFilter.py** (New)
   - Monitors CryptoPanic and CoinGecko for high-impact news
   - Pauses trading during major events (FOMC, Fed, SEC, hacks, etc.)
   - 5-minute cache to avoid excessive API calls

3. **DailyLimits.py** (New)
   - Tracks daily PnL in real-time
   - Enforces daily profit target (8% → stop trading)
   - Enforces daily loss limit (-3% → 24h pause)
   - Tracks trade count (max 10 per day)

## Integration Steps

### Step 1: Update Your Main Trading Loop

In your main trading file (e.g., `LiveTrading.py` or `LiveTrading_Beast.py`), add these imports at the top:

```python
from NewsFilter import should_pause_trading
from DailyLimits import DailyLimitsManager
from ProfitManager import manage_open_positions
```

### Step 2: Initialize Daily Limits Manager

In your main initialization code:

```python
from LiveTradingConfig import API_KEY, API_SECRET, testnet

# Initialize daily limits manager
daily_limits = DailyLimitsManager(API_KEY, API_SECRET, testnet)
```

### Step 3: Add Checks to Your Main Loop

In your main trading loop (where you check for new signals), add these checks BEFORE placing new trades:

```python
# ============ ANTI-DEGEN CHECKS ============

# 1. Check news filter
should_pause_news, news_reason = should_pause_trading()
if should_pause_news:
    logging.info(f"[NEWS FILTER] {news_reason}")
    time.sleep(300)  # Wait 5 minutes before checking again
    continue

# 2. Check daily limits
should_pause_limits, limits_reason = daily_limits.check_daily_limits()
if should_pause_limits:
    logging.info(f"[DAILY LIMITS] {limits_reason}")
    time.sleep(60)  # Wait 1 minute before checking again
    continue

# 3. Manage open positions (profit taking)
manage_open_positions()

# ============ NOW SAFE TO TRADE ============
# Your normal trading logic here...
```

### Step 4: Log Trades to Daily Limits

When a trade closes (in your trade management code), log it:

```python
# After a position closes
daily_limits.log_trade(symbol, direction, pnl_usdt, pnl_percent)
```

## Configuration

Edit these constants in the respective files:

### DailyLimits.py
```python
MAX_TRADES_PER_DAY = 10        # Max trades before pause
DAILY_PNL_TARGET = 8.0         # 8% profit → stop trading
DAILY_LOSS_LIMIT = -3.0        # -3% loss → 24h pause
```

### ProfitManager.py
```python
# Real 10% TP (accounts for 0.15% fees)
if real_roi_percent >= 10.3:   # Aim for 10.3% to net 10%
    close_position(symbol, qty)

# Real 4% partial exit (80% close, 20% runner)
if real_roi_percent >= 4.2:    # Aim for 4.2% to net 4%
    close_qty = round(abs(qty) * 0.8, 3)
    close_position(symbol, close_qty)
```

### NewsFilter.py
```python
BAD_KEYWORDS = [
    'fomc', 'fed', 'cpi', 'ppi', 'sec', 'liquidation', 'etf decision',
    'binance', 'hack', 'exploit', 'breach', 'bankruptcy', 'collapse',
    'emergency', 'crisis', 'crash', 'circuit breaker', 'halt', 'suspend'
]
```

## Example Integration (Minimal)

```python
import logging
import time
from NewsFilter import should_pause_trading
from DailyLimits import DailyLimitsManager
from ProfitManager import manage_open_positions
from LiveTradingConfig import API_KEY, API_SECRET, testnet

# Setup
daily_limits = DailyLimitsManager(API_KEY, API_SECRET, testnet)

# Main loop
while True:
    try:
        # Anti-degen checks
        should_pause_news, news_reason = should_pause_trading()
        if should_pause_news:
            logging.info(f"[NEWS] {news_reason}")
            time.sleep(300)
            continue
        
        should_pause_limits, limits_reason = daily_limits.check_daily_limits()
        if should_pause_limits:
            logging.info(f"[LIMITS] {limits_reason}")
            time.sleep(60)
            continue
        
        # Manage profits
        manage_open_positions()
        
        # Your trading logic here...
        # ...
        
        time.sleep(1)
    
    except Exception as e:
        logging.error(f"Main loop error: {e}")
        time.sleep(5)
```

## Monitoring

### Check Daily Limits Status

```python
status = daily_limits.get_status()
print(status)
# Output:
# {
#   'date': '2025-11-28',
#   'trades_count': 3,
#   'max_trades': 10,
#   'daily_pnl_percent': 2.5,
#   'daily_pnl_target': 8.0,
#   'daily_loss_limit': -3.0,
#   'is_paused': False,
#   'pause_reason': '',
#   'trades': [...]
# }
```

### Manual Reset (if needed)

```python
daily_limits.reset_daily_limits()
```

## Files Generated

- `daily_limits.json` - Daily tracking data (auto-created)
- `news_cache.json` - News cache (auto-created)
- `bot_trades.csv` - Trade log (already existed, now enhanced)

## Testing

### Test News Filter
```bash
python NewsFilter.py
```

### Test Daily Limits
```bash
python DailyLimits.py
```

### Test ProfitManager
```bash
python ProfitManager.py
```

## Key Features

✅ **Slippage Protection**: Limit orders with 0.5% buffer + fallback to market  
✅ **Real 10% TP**: Accounts for 0.15% fees/slippage  
✅ **Partial Exits**: 80% close at +4%, keep 20% for runners  
✅ **News Blocker**: Pauses during FOMC, Fed, SEC, hacks, etc.  
✅ **Daily Profit Target**: Stop trading after +8% daily PnL  
✅ **Daily Loss Limit**: 24h pause after -3% daily loss  
✅ **Trade Counter**: Max 10 trades per day  
✅ **No Stop Loss**: Let winners run, only take profits  

## Troubleshooting

### News API not working?
- NewsFilter gracefully falls back if APIs are unavailable
- Check internet connection
- Verify CryptoPanic/CoinGecko are accessible

### Daily limits not resetting?
- Check `daily_limits.json` file
- Verify system date/time is correct
- Manually reset with `daily_limits.reset_daily_limits()`

### Slippage orders not filling?
- Increase the 0.5% buffer in `close_position()`
- Check Binance testnet liquidity
- Verify order quantity is above minimum

---

**Ready to trade smarter! 🚀**
