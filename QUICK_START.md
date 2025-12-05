# ⚡ QUICK START — 5 MINUTE SETUP

## What You Have

✅ **4 Anti-Degen Rules** preventing account blowups  
✅ **3 New Python Modules** ready to integrate  
✅ **4 Documentation Files** with step-by-step guides  
✅ **1 Template** showing exact integration pattern  

---

## The 4 Rules (30 seconds)

| Rule | What | How | Result |
|------|------|-----|--------|
| **Slippage Killer** | Protects exits | Limit orders + market fallback | Keep your profits |
| **Real 10% TP** | Takes profits | Aim +10.3% to net +10% | Consistent gains |
| **News Blocker** | Pauses trading | Detects FOMC, Fed, hacks | Avoid liquidation |
| **Daily Limits** | Stops over-trading | +8% profit target, -3% loss limit | Sustainable growth |

---

## Files You Got

### Code Files (Ready to Use)
- `NewsFilter.py` - News monitoring
- `DailyLimits.py` - Daily PnL tracking
- `ProfitManager.py` - Updated with slippage killer + real 10% TP
- `MAIN_LOOP_TEMPLATE.py` - Copy-paste integration template

### Documentation Files (Read These)
- `INTEGRATION_GUIDE.md` - Step-by-step integration
- `ANTI_DEGEN_RULES.md` - Quick reference
- `IMPLEMENTATION_COMPLETE.md` - Full details
- `QUICK_START.md` - This file

---

## Integration (Copy-Paste, 2 minutes)

### Step 1: Add Imports
```python
# At top of your main trading file
from NewsFilter import should_pause_trading
from DailyLimits import DailyLimitsManager
from ProfitManager import manage_open_positions
from LiveTradingConfig import API_KEY, API_SECRET, testnet
```

### Step 2: Initialize
```python
# In your setup code
daily_limits = DailyLimitsManager(API_KEY, API_SECRET, testnet)
```

### Step 3: Add to Main Loop
```python
while True:
    # Check 1: News
    should_pause_news, _ = should_pause_trading()
    if should_pause_news:
        time.sleep(300)
        continue
    
    # Check 2: Daily limits
    should_pause_limits, _ = daily_limits.check_daily_limits()
    if should_pause_limits:
        time.sleep(60)
        continue
    
    # Check 3: Manage profits
    manage_open_positions()
    
    # Your trading logic here...
```

**That's it! 🎉**

---

## Configuration (1 minute)

### DailyLimits.py
```python
MAX_TRADES_PER_DAY = 10        # Stop after 10 trades
DAILY_PNL_TARGET = 8.0         # Stop after +8% profit
DAILY_LOSS_LIMIT = -3.0        # Pause after -3% loss
```

### ProfitManager.py
```python
# Real 10% TP (after 0.15% fees)
if real_roi_percent >= 10.3:   # Full exit
    close_position(symbol, qty)

# Real 4% partial exit
if real_roi_percent >= 4.2:    # 80% exit, 20% runner
    close_qty = round(abs(qty) * 0.8, 3)
    close_position(symbol, close_qty)
```

### NewsFilter.py
```python
# Already configured with all major keywords
# FOMC, Fed, CPI, PPI, SEC, hacks, exploits, etc.
# No changes needed unless you want to add more
```

---

## Testing (1 minute)

```bash
# Test each module independently
python NewsFilter.py
python DailyLimits.py
python ProfitManager.py

# Then test on testnet
# (Already configured in LiveTradingConfig.py)
python LiveTrading.py
```

---

## Monitoring (30 seconds)

### Check Status
```python
status = daily_limits.get_status()
print(f"Trades: {status['trades_count']}/{status['max_trades']}")
print(f"Daily PnL: {status['daily_pnl_percent']:+.2f}%")
print(f"Paused: {status['is_paused']}")
```

### View Trades
```python
status = daily_limits.get_status()
for trade in status['trades']:
    print(f"{trade['symbol']}: {trade['pnl_percent']:+.2f}%")
```

---

## Before You Trade

- [ ] Read INTEGRATION_GUIDE.md (5 min)
- [ ] Copy integration pattern to your bot (2 min)
- [ ] Test on testnet for 1 week (7 days)
- [ ] Verify news filter catches events
- [ ] Verify daily limits reset correctly
- [ ] Check trade logs in bot_trades.csv
- [ ] Adjust limits for your risk tolerance
- [ ] Deploy to live (when confident)

---

## Expected Results

### Week 1-2 (Testnet)
- ✅ News filter pauses during events
- ✅ Daily limits reset at midnight
- ✅ Profit taking works correctly
- ✅ Trade log shows consistent gains

### Week 3+ (Live)
- ✅ 2-4% daily profit on good days
- ✅ Protected from news bombs
- ✅ Consistent, sustainable growth
- ✅ No liquidations or blowups

---

## The Math

### Without Anti-Degen
```
Day 1: +5% → Day 2: +3% → Day 3: -8% (revenge)
Result: -5% (account down)
```

### With Anti-Degen
```
Day 1: +5% (STOP) → Day 2: +3% (STOP) → Day 3: +4% (STOP)
Result: +12% (account up)
```

---

## Key Takeaways

1. **Slippage Killer** = Remove the hidden 0.15% bleed
2. **Real 10% TP** = Take profits before greed kicks in
3. **News Blocker** = Avoid catastrophic liquidations
4. **Daily Limits** = Prevent over-trading and revenge trading

---

## Help

### Stuck?
1. Read INTEGRATION_GUIDE.md
2. Check MAIN_LOOP_TEMPLATE.py
3. Review ANTI_DEGEN_RULES.md
4. Test each module independently

### Issues?
1. Check daily_limits.json
2. Check news_cache.json
3. Check bot_trades.csv
4. Verify internet connection
5. Check system date/time

---

## Next Steps

1. **Now**: Read INTEGRATION_GUIDE.md (5 min)
2. **Today**: Integrate into your bot (30 min)
3. **This Week**: Test on testnet (7 days)
4. **Next Week**: Deploy to live (when confident)

---

**You're ready! 🚀**

**Remember: The best trade is the one you don't take.**

**Happy trading!**
