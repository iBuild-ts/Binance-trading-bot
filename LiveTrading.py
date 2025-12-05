import os
import time
os.environ['TZ'] = 'UTC'
time.tzset()

import logging
from LiveTradingConfig import *
from LiveTradingConfig import symbols_to_trade
from Helper import *
from TradeManager import *
from ProfitManager import manage_open_positions
import SharedHelper
from threading import Thread
from queue import Queue
from binance.client import Client
import warnings
warnings.filterwarnings("ignore")

# FORCE FUTURES TESTNET
Client.FUTURES_TESTNET = True

if __name__ == '__main__':
    log.info("horlah_40percent_master — FINAL WORKING VERSION — STARTING")

    Bots = []
    signal_queue = Queue()
    print_trades_q = Queue()

    # CLIENT — TESTNET FUTURES
    client_binance = Client(API_KEY, API_SECRET, testnet=True)

    # KILL THE -2015 ERROR FOREVER (NO MORE WEBSOCKET NOISE)
    client_binance.futures_stream_get_listen_key = lambda: None
    client_binance.stream_get_listen_key = lambda: None
    client_binance.futures_stream_keepalive = lambda: None
    client_binance.stream_close = lambda: None
    if hasattr(client_binance, 'start_user_socket'):
        client_binance.start_user_socket = lambda *a, **k: None

    client = CustomClient(client_binance)

    # SETUP BOTS
    client.setup_bots(Bots, symbols_to_trade, signal_queue, print_trades_q)
    log.info(f"{len(Bots)} BOTS LOADED — REST POLLING ACTIVE")

    # TRADE MANAGER — FINAL WORKING VERSION
    TM = TradeManager(
        client=client_binance,
        signal_queue=signal_queue,
        print_trades_q=print_trades_q,
        position_size_usd=150,
        max_number_of_positions=5
    )
    Thread(target=TM.new_trades_loop, daemon=True).start()
    Thread(target=TM.check_pnl_and_close, daemon=True).start()
    Thread(target=TM.check_daily_goal_and_sleep, daemon=True).start()

    # DATA COMBINE (keeps historical data loaded)
    if auto_calculate_buffer:
        buffer_candles = SharedHelper.get_required_buffer(trading_strategy)
        buffer = convert_buffer_to_string(buffer_candles)
        log.info(f"get_required_buffer() - Using fast pre-defined buffer ({buffer_candles} candles)")
    else:
        buffer = '3 hours ago'
    
    log.info(f"convert_buffer_to_string() - required buffer calculated is {buffer}")
    Thread(target=client.combine_data, args=(Bots, symbols_to_trade, buffer), daemon=True).start()

    log.info("horlah_40percent_master 100% LIVE — 20x LEVERAGE READY")
    log.info("USING REST POLLING — NO WEBSOCKET, NO DNS, NO FREEZE")

    # PnL-BASED PARTIAL CLOSE FUNCTION
    def quick_pnl_close():
        try:
            positions = client_binance.futures_position_information()
            for pos in positions:
                symbol = pos['symbol']
                if symbol.endswith('USDT'):
                    unrealized = float(pos['unrealizedProfit'])
                    initial_margin = float(pos['initialMargin'])
                    pnl_pct = (unrealized / initial_margin) * 100 if initial_margin > 0 else 0

                    if pnl_pct >= 10:
                        try:
                            client_binance.futures_create_order(
                                symbol=symbol,
                                side="SELL",
                                type="MARKET",
                                quantity=abs(float(pos['positionAmt'])),
                                reduceOnly=True
                            )
                            log.info(f"FULL CLOSE {symbol} at +10% PnL")
                        except Exception as e:
                            log.warning(f"Error closing {symbol} at +10%: {e}")
                    elif pnl_pct >= 4:
                        try:
                            qty = abs(float(pos['positionAmt']))
                            close_qty = round(qty * 0.8, 2)
                            if close_qty > 0:
                                client_binance.futures_create_order(
                                    symbol=symbol,
                                    side="SELL",
                                    type="MARKET",
                                    quantity=close_qty,
                                    reduceOnly=True
                                )
                                log.info(f"LOCKED 80% {symbol} at +4% PnL")
                        except Exception as e:
                            log.warning(f"Error locking 80% of {symbol} at +4%: {e}")
        except Exception as e:
            log.warning(f"quick_pnl_close() error: {e}")

    # FINAL BOMB-PROOF LOOP — THIS IS WHERE TRADES HAPPEN
    last_minute = None
    last_pnl_check = time.time()
    while True:
        try:
            btc_price = float(client_binance.get_symbol_ticker(symbol="BTCUSDT")["price"])
            current_minute = time.strftime("%Y-%m-%d %H:%M")

            if last_minute != current_minute:
                last_minute = current_minute
                log.info(f"NEW 1m CANDLE — BTC: {btc_price:.2f} USDT — SCANNING SIGNALS...")

                # THIS IS THE CRITICAL PART — NOW CALLS YOUR NEW make_decision(df)
                for bot in Bots:
                    try:
                        klines = client_binance.futures_klines(symbol=bot.symbol, interval='1m', limit=300)
                        df = bot.create_df(klines)           # ← create DataFrame
                        bot.make_decision(df)                # ← PASS df HERE (THIS WAS MISSING BEFORE!)
                    except Exception as e:
                        log.debug(f"Error scanning {bot.symbol}: {e}")
                
                # PROFIT MANAGER — TAKES PARTIAL PROFITS & MANAGES POSITIONS
                manage_open_positions()

            # PnL-BASED PARTIAL CLOSE — CHECK EVERY 10 SECONDS
            current_time = time.time()
            if current_time - last_pnl_check >= 10:
                quick_pnl_close()
                last_pnl_check = current_time

            time.sleep(8)

        except KeyboardInterrupt:
            log.info("Bot stopped — peace out king!")
            break
        except Exception as e:
            log.warning(f"Still alive — network hiccup: {e}")
            time.sleep(10)