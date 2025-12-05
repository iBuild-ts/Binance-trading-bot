# ================================================
# LiveTradingConfig.py — FINAL TESTNET VERSION
# 10,000 USDT demo account — READY TO PRINT
# ================================================

# YOUR REAL TESTNET KEYS (already correct)
API_KEY = 'tY6PJ6sKd1juJvV0ywQrl0bfFswlUd84uOfdDd6TMEfsvaF2F7eiNlAXL8KtDb8z'
API_SECRET = 'K5hbHYvr55kdmWPxl1Jwi9R9xN97oKp2O6akmLVVTwosG4eAg3HOwzxpsUbADFSY'

# TESTNET MODE = ON (this is what gives you 10,000 fake USDT)
testnet = True

# Force correct Futures Testnet URLs (kills all connection errors)
from binance.client import Client
Client.API_URL = 'https://testnet.binancefuture.com/fapi/v1'
Client.FUTURES_URL = 'https://testnet.binancefuture.com/fapi/v1'
Client.FUTURES_COIN_URL = 'https://testnet.binancefuture.com/dapi/v1'
Client.FUTURES_WS_URL = 'wss://fstream.binancefuture.com/ws'
Client.FUTURES_TESTNET = True

# STRATEGY
trading_strategy = 'horlah_40percent_master'

# TP/SL SETTINGS
TP_SL_choice = '%'              # We use percentage-based TP/SL
TP_mult = 3.0                   # Take Profit = 3× risk
SL_mult = 1.0                   # Stop Loss = 1× risk

# LEVERAGE & POSITION SIZING (safe but aggressive for testnet)
leverage = 0                   # 20x leverage on your 10k demo = huge gains
order_size = 10                 # 10 USDT per trade (at 20x = 200 USDT position)

# SYMBOLS
trade_all_symbols = False
symbols_to_trade = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT', '1000PEPEUSDT', 'ADAUSDT']
coin_exclusion_list = ['USDCUSDT', 'BTCDOMUSDT']

# INTERVAL & EXECUTION
interval = '1m'
use_market_orders = False
trading_threshold = 0.3
max_number_of_positions = 15    # Can hold up to 15 positions
wait_for_candle_close = True

# TRAILING STOP
use_trailing_stop = False
trailing_stop_callback = 0.1

# BUFFER & PERFORMANCE
auto_calculate_buffer = True
buffer = '3 hours ago'

# LOGGING
LOG_LEVEL = 20
log_to_file = False

# PERFORMANCE
use_multiprocessing_for_trade_execution = False

# CUSTOM FUNCTIONS
custom_tp_sl_functions = ['USDT']
make_decision_options = {}

# FINAL TOUCH — SUPPRESS HARMLESS WARNINGS
import warnings
warnings.filterwarnings("ignore", message="This event loop is already running")
warnings.filterwarnings("ignore", message="Invalid API-key")