# 🚀 HOW TO START THE BOT

## Quick Start (5 Minutes)

### Step 1: Activate Virtual Environment
```bash
cd /Users/horlahdefi/Binance-trading-bot
source venv/bin/activate
```

### Step 2: Start the Bot
```bash
# Option A: Run existing bot (with anti-degen already integrated)
python LiveTrading.py

# Option B: Run Beast mode strategy
python LiveTrading_Beast.py

# Option C: Run Beast v2
python LiveTrading_Beast_v2.py

# Option D: Run Pro version
python LiveTrading_Pro.py
```

**That's it! Bot is running.** ✅

---

## Before You Start (Important!)

### ✅ Pre-Start Checklist

- [ ] Virtual environment activated: `source venv/bin/activate`
- [ ] You're in the correct directory: `/Users/horlahdefi/Binance-trading-bot`
- [ ] Dependencies installed: `pip list | grep python-binance`
- [ ] API keys configured in `LiveTradingConfig.py`
- [ ] Testnet mode enabled (already configured)
- [ ] Anti-degen modules integrated (see below)

---

## Integration Steps (If Not Already Done)

### Step 1: Add Imports to Your Main Trading File

Open `LiveTrading.py` (or whichever you use) and add at the top:

```python
from NewsFilter import should_pause_trading
from DailyLimits import DailyLimitsManager
from ProfitManager import manage_open_positions
```

### Step 2: Initialize Daily Limits Manager

In your initialization code (after creating the client), add:

```python
from LiveTradingConfig import API_KEY, API_SECRET, testnet

# Initialize daily limits manager
daily_limits = DailyLimitsManager(API_KEY, API_SECRET, testnet)
```

### Step 3: Add Checks to Main Loop

In your main trading loop (before placing new trades), add:

```python
# ============ ANTI-DEGEN CHECKS ============

# 1. Check news filter
should_pause_news, news_reason = should_pause_trading()
if should_pause_news:
    logging.info(f"[NEWS FILTER] {news_reason}")
    time.sleep(300)  # Wait 5 minutes
    continue

# 2. Check daily limits
should_pause_limits, limits_reason = daily_limits.check_daily_limits()
if should_pause_limits:
    logging.info(f"[DAILY LIMITS] {limits_reason}")
    time.sleep(60)  # Wait 1 minute
    continue

# 3. Manage open positions (profit taking)
manage_open_positions()

# ============ NOW SAFE TO TRADE ============
# Your normal trading logic here...
```

**See MAIN_LOOP_TEMPLATE.py for complete example.**

---

## Starting the Bot (Step by Step)

### Terminal Commands

```bash
# 1. Navigate to bot directory
cd /Users/horlahdefi/Binance-trading-bot

# 2. Activate virtual environment
source venv/bin/activate

# 3. Verify environment is active (you should see (venv) prefix)
# Example: (venv) horlahdefi@MacBook Binance-trading-bot %

# 4. Start the bot
python LiveTrading.py
```

### What You Should See

```
2025-11-28 15:57:10 - INFO - 🚀 Starting trading bot with anti-degen protections...
2025-11-28 15:57:11 - INFO - ✅ Connected to Binance Testnet
2025-11-28 15:57:12 - INFO - 📊 Account Balance: 10,000.00 USDT
2025-11-28 15:57:13 - INFO - [MONEY PRINTER] BTCUSDT LONG → REAL PNL: +2.45% (+24.50 USDT)
2025-11-28 15:57:14 - INFO - ✅ SLIPPAGE-PROTECTED CLOSE → 0.001234 BTCUSDT @ 43,250.00
2025-11-28 15:57:15 - INFO - ✅ Trade logged: BTCUSDT LONG +2.45%
```

---

## Monitoring While Running

### Check Daily Status (In Another Terminal)

```bash
# While bot is running, open another terminal
cd /Users/horlahdefi/Binance-trading-bot
source venv/bin/activate

# Check daily limits status
python -c "
from DailyLimits import DailyLimitsManager
from LiveTradingConfig import API_KEY, API_SECRET, testnet
manager = DailyLimitsManager(API_KEY, API_SECRET, testnet)
status = manager.get_status()
print(f\"Trades: {status['trades_count']}/{status['max_trades']}\")
print(f\"Daily PnL: {status['daily_pnl_percent']:+.2f}%\")
print(f\"Paused: {status['is_paused']}\")
"
```

### View Trade Log

```bash
# View recent trades
tail -20 bot_trades.csv

# Or open in your editor
cat bot_trades.csv
```

### Check Generated Files

```bash
# Check daily limits tracking
cat daily_limits.json

# Check news cache
cat news_cache.json

# Check trade log
cat bot_trades.csv
```

---

## Stopping the Bot

### Method 1: Keyboard Interrupt (Graceful)
```bash
# Press Ctrl+C in the terminal where bot is running
# Bot will stop gracefully and print final status
```

### Method 2: Kill Process (If Stuck)
```bash
# In another terminal
ps aux | grep LiveTrading.py
kill -9 <process_id>
```

### Method 3: Close Terminal
```bash
# Simply close the terminal window
# (Less graceful, but works)
```

---

## Configuration Before Starting

### Edit LiveTradingConfig.py

```python
# Trading strategy
trading_strategy = 'horlah_40percent_master'

# Leverage & position sizing
leverage = 20                   # 20x leverage
order_size = 10                 # 10 USDT per trade

# Symbols to trade
symbols_to_trade = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT',
    'XRPUSDT', 'DOGEUSDT', '1000PEPEUSDT', 'ADAUSDT'
]

# Interval
interval = '1m'                 # 1-minute candles

# Max positions
max_number_of_positions = 15    # Can hold up to 15 positions
```

### Edit DailyLimits.py (Optional)

```python
MAX_TRADES_PER_DAY = 10        # Stop after 10 trades
DAILY_PNL_TARGET = 8.0         # Stop after +8% profit
DAILY_LOSS_LIMIT = -3.0        # Pause after -3% loss
```

### Edit ProfitManager.py (Optional)

```python
# Real 10% TP (after 0.15% fees)
if real_roi_percent >= 10.3:   # Full exit
    close_position(symbol, qty)

# Real 4% partial exit
if real_roi_percent >= 4.2:    # 80% exit, 20% runner
    close_qty = round(abs(qty) * 0.8, 3)
    close_position(symbol, close_qty)
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'NewsFilter'"

**Solution**: Make sure you're in the correct directory and virtual environment is activated.

```bash
cd /Users/horlahdefi/Binance-trading-bot
source venv/bin/activate
python LiveTrading.py
```

### Issue: "API Connection Error"

**Solution**: Check your internet connection and Binance API status.

```bash
# Test connection
python -c "from binance import Client; print('✅ Binance API OK')"
```

### Issue: "Insufficient Margin"

**Solution**: This is normal on testnet. The bot will skip trades that don't have enough margin.

### Issue: Bot Not Trading

**Solution**: Check if daily limits or news filter is pausing the bot.

```bash
# Check daily limits status
cat daily_limits.json

# Check if paused
python -c "
from DailyLimits import DailyLimitsManager
from LiveTradingConfig import API_KEY, API_SECRET, testnet
manager = DailyLimitsManager(API_KEY, API_SECRET, testnet)
status = manager.get_status()
print(f'Paused: {status[\"is_paused\"]}')
print(f'Reason: {status[\"pause_reason\"]}')
"
```

### Issue: "Cannot find venv"

**Solution**: Create virtual environment again.

```bash
cd /Users/horlahdefi/Binance-trading-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Running on Different Modes

### Mode 1: Standard LiveTrading
```bash
python LiveTrading.py
```
- Basic trading with anti-degen protections
- Good for beginners
- Stable and reliable

### Mode 2: Beast Mode
```bash
python LiveTrading_Beast.py
```
- More aggressive strategy
- Higher risk, higher reward
- For experienced traders

### Mode 3: Beast Mode v2
```bash
python LiveTrading_Beast_v2.py
```
- Improved Beast mode
- Better risk management
- Recommended for most traders

### Mode 4: Pro Mode
```bash
python LiveTrading_Pro.py
```
- Advanced features
- Multiple strategies
- For professional traders

---

## Monitoring Dashboard

### Real-Time Monitoring

```bash
# Terminal 1: Run the bot
python LiveTrading.py

# Terminal 2: Monitor status (run every 10 seconds)
watch -n 10 'python -c "
from DailyLimits import DailyLimitsManager
from LiveTradingConfig import API_KEY, API_SECRET, testnet
manager = DailyLimitsManager(API_KEY, API_SECRET, testnet)
status = manager.get_status()
print(f\"Trades: {status[\"trades_count\"]}/{status[\"max_trades\"]}\")
print(f\"Daily PnL: {status[\"daily_pnl_percent\"]:+.2f}%\")
print(f\"Paused: {status[\"is_paused\"]}\")
"'
```

### View Logs

```bash
# View last 20 lines of trade log
tail -20 bot_trades.csv

# View with timestamps
tail -20 bot_trades.csv | column -t -s,

# Watch for new trades in real-time
tail -f bot_trades.csv
```

---

## Daily Workflow

### Morning (Start of Day)

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Check yesterday's performance
cat daily_limits.json

# 3. Start the bot
python LiveTrading.py

# 4. Monitor first hour
# Watch for any errors or issues
```

### During Day

```bash
# Check status periodically
python -c "
from DailyLimits import DailyLimitsManager
from LiveTradingConfig import API_KEY, API_SECRET, testnet
manager = DailyLimitsManager(API_KEY, API_SECRET, testnet)
status = manager.get_status()
print(f'Trades: {status[\"trades_count\"]}/{status[\"max_trades\"]}')
print(f'Daily PnL: {status[\"daily_pnl_percent\"]:+.2f}%')
"
```

### Evening (End of Day)

```bash
# 1. Check final status
cat daily_limits.json

# 2. Review trades
tail -20 bot_trades.csv

# 3. Stop the bot (Ctrl+C)
# Or let it run overnight

# 4. Analyze performance
# Review daily_limits.json for insights
```

---

## Performance Monitoring

### Check Win Rate

```bash
# Count winning trades
grep "+" bot_trades.csv | wc -l

# Count losing trades
grep "-" bot_trades.csv | wc -l

# Calculate win rate
python -c "
import csv
wins = 0
losses = 0
with open('bot_trades.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        pnl = float(row['PNL_Percent'].rstrip('%'))
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1
total = wins + losses
if total > 0:
    print(f'Win Rate: {wins}/{total} ({100*wins/total:.1f}%)')
"
```

### Check Average Profit

```bash
python -c "
import csv
total_pnl = 0
count = 0
with open('bot_trades.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        pnl = float(row['PNL_Percent'].rstrip('%'))
        total_pnl += pnl
        count += 1
if count > 0:
    avg = total_pnl / count
    print(f'Average PnL: {avg:+.2f}%')
    print(f'Total Trades: {count}')
    print(f'Total PnL: {total_pnl:+.2f}%')
"
```

---

## Quick Reference

| Command | What It Does |
|---------|-------------|
| `source venv/bin/activate` | Activate virtual environment |
| `python LiveTrading.py` | Start the bot |
| `Ctrl+C` | Stop the bot gracefully |
| `tail -20 bot_trades.csv` | View last 20 trades |
| `cat daily_limits.json` | Check daily status |
| `cat news_cache.json` | Check news cache |
| `python NewsFilter.py` | Test news filter |
| `python DailyLimits.py` | Test daily limits |
| `python ProfitManager.py` | Test profit manager |
| `bash VERIFY_INSTALLATION.sh` | Verify installation |

---

## Next Steps

1. **Activate environment**: `source venv/bin/activate`
2. **Start bot**: `python LiveTrading.py`
3. **Monitor trades**: `tail -f bot_trades.csv`
4. **Check status**: `cat daily_limits.json`
5. **Review performance**: Analyze `bot_trades.csv`

---

## Support

- **QUICK_START.md** - 5-minute setup guide
- **INTEGRATION_GUIDE.md** - Integration instructions
- **MAIN_LOOP_TEMPLATE.py** - Code template
- **DEPLOYMENT_CHECKLIST.md** - Pre-deployment checklist

---

**Ready to start? Run this now:**

```bash
cd /Users/horlahdefi/Binance-trading-bot
source venv/bin/activate
python LiveTrading.py
```

**Happy trading! 🚀**
