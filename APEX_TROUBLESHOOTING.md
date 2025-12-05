# 🔧 PROJECT APEX — TROUBLESHOOTING GUIDE

## Connection Error Fixes

### Issue: "Max retries exceeded" / "Failed to resolve 'testnet.binancefuture.com'"

**Root Cause**: Network connectivity issues with Binance testnet API

**Solutions**:

#### 1. Check Internet Connection
```bash
ping google.com
```

#### 2. Check Binance API Status
```bash
curl -s https://testnet.binancefuture.com/fapi/v1/ping
```

Expected response: `{}`

#### 3. Verify API Keys
```bash
python -c "
from binance import Client
API_KEY = 'tY6PJ6sKd1juJvV0ywQrl0bfFswlUd84uOfdDd6TMEfsvaF2F7eiNlAXL8KtDb8z'
API_SECRET = 'K5hbHYvr55kdmWPxl1Jwi9R9xN97oKp2O6akmLVVTwosG4eAg3HOwzxpsUbADFSY'
client = Client(api_key=API_KEY, api_secret=API_SECRET, testnet=True)
print('✅ API connection OK')
"
```

#### 4. Check DNS Resolution
```bash
nslookup testnet.binancefuture.com
```

#### 5. Restart the Bot
```bash
# Stop current instance (Ctrl+C)
# Wait 30 seconds
python APEX_TRADER.py
```

---

## Error Messages Explained

### "HTTPSConnectionPool... Max retries exceeded"
- **Meaning**: Network timeout or API unreachable
- **Fix**: Wait 1-2 minutes, bot will retry automatically with exponential backoff

### "Failed to resolve 'testnet.binancefuture.com'"
- **Meaning**: DNS resolution failure
- **Fix**: Check internet connection, restart bot

### "Connection aborted. RemoteDisconnected"
- **Meaning**: API closed connection unexpectedly
- **Fix**: Temporary issue, bot retries automatically

### "Analysis error for BTCUSDT: '2'"
- **Meaning**: DataFrame column access error (fixed in latest version)
- **Fix**: Update APEX_TRADER.py to latest version

---

## Connection Retry Logic (Automatic)

APEX_TRADER.py now includes automatic retry logic:

```python
# Retry with exponential backoff
# Attempt 1: Wait 1 second
# Attempt 2: Wait 2 seconds
# Attempt 3: Wait 4 seconds
# Max 3 attempts per request
```

**What this means**:
- ✅ Bot automatically retries failed requests
- ✅ Waits longer between retries (exponential backoff)
- ✅ Continues trading if connection recovers
- ✅ Gracefully handles temporary outages

---

## Monitoring Connection Health

### Check Connection Failures
```bash
# In APEX logs, look for:
# "Connection failures: 5"
# This shows how many connection errors occurred
```

### View Real-Time Status
```bash
# Terminal 1: Run APEX
python APEX_TRADER.py

# Terminal 2: Monitor logs
tail -f APEX_TRADER.log 2>/dev/null || echo "Logs in console"
```

---

## Network Optimization

### 1. Use Stable Internet
- Wired connection preferred over WiFi
- Avoid VPN if possible
- Check WiFi signal strength

### 2. Reduce API Calls
Current settings:
- Analysis every 3 minutes (180 seconds)
- 2 API calls per symbol (4h + 15m klines)
- 1 price tick per symbol
- Total: ~9 API calls per cycle

### 3. Increase Retry Delays
Edit `APEX_TRADER.py`:
```python
# Line 131-132: Increase base_delay
df_4h = retry_with_backoff(fetch_4h, max_retries=4, base_delay=2)
df_15m = retry_with_backoff(fetch_15m, max_retries=4, base_delay=2)
```

---

## Binance Testnet Status

### Check Testnet Status
```bash
curl -s https://testnet.binancefuture.com/fapi/v1/exchangeInfo | head -20
```

### Testnet Maintenance Windows
- Usually: Tuesday 6:00-8:00 UTC
- Check: https://testnet.binancefuture.com/

---

## Graceful Error Handling

APEX_TRADER.py now handles errors gracefully:

```
✅ News filter error → Continue trading
✅ Daily limits error → Continue trading
✅ Profit manager error → Continue trading
✅ Analysis error → Skip symbol, try next
✅ Connection error → Retry with backoff
```

**Result**: Bot stays running even during temporary issues

---

## Performance Metrics

### Connection Health
- **Connection failures**: Tracked in state
- **Retry attempts**: Logged with timestamps
- **Success rate**: Should be 95%+ after fixes

### Expected Behavior
```
14:22:25 | 🔍 APEX ANALYSIS CYCLE | Trades: 0/8 | Connection failures: 2
14:22:33 | Analysis error for BTCUSDT: Connection aborted (retrying...)
14:22:34 | ✅ BTCUSDT analysis successful
14:22:37 | 📊 BTCUSDT → LONG | Conviction: 0.95 | Bias: BULLISH
```

---

## Quick Fixes (Try These First)

### 1. Restart Bot
```bash
# Press Ctrl+C
# Wait 30 seconds
python APEX_TRADER.py
```

### 2. Check Internet
```bash
ping 8.8.8.8
```

### 3. Verify API
```bash
python -c "from binance import Client; Client(testnet=True).ping()"
```

### 4. Check Binance Status
Visit: https://status.binance.com/

### 5. Update APEX_TRADER.py
```bash
# Get latest version with connection fixes
git pull origin main
```

---

## Advanced Debugging

### Enable Debug Logging
Edit `APEX_TRADER.py`:
```python
# Line 36-40
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
```

### Test Individual Components
```bash
# Test Binance connection
python -c "
from binance import Client
c = Client(testnet=True)
print('Ping:', c.ping())
print('Time:', c.get_server_time())
"

# Test data fetching
python -c "
from binance import Client
c = Client(testnet=True)
klines = c.futures_klines(symbol='BTCUSDT', interval='4h', limit=5)
print(f'Got {len(klines)} klines')
"
```

---

## When to Contact Support

If you've tried all fixes and still getting errors:

1. **Note the error message**
2. **Check timestamp**
3. **Note which symbol(s) fail**
4. **Check internet connection**
5. **Verify API keys**
6. **Check Binance status page**

---

## Summary

**APEX_TRADER.py now includes**:
- ✅ Automatic retry logic with exponential backoff
- ✅ Graceful error handling (continues trading on errors)
- ✅ Connection failure tracking
- ✅ Better error messages
- ✅ Improved DataFrame column handling

**Expected result**:
- ✅ Fewer connection errors
- ✅ Automatic recovery from temporary outages
- ✅ Bot stays running longer
- ✅ Better reliability

**Status**: ✅ FIXED & READY

---

**Last Updated**: December 2, 2025  
**Version**: APEX_TRADER.py v2 (Connection Hardened)
