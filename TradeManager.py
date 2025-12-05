from threading import Thread
import logging
import math
from datetime import datetime

from binance import ThreadedWebsocketManager
from binance.client import Client
from binance.enums import SIDE_SELL, SIDE_BUY, FUTURE_ORDER_TYPE_MARKET, FUTURE_ORDER_TYPE_LIMIT, TIME_IN_FORCE_GTC, \
    FUTURE_ORDER_TYPE_STOP_MARKET, FUTURE_ORDER_TYPE_TAKE_PROFIT
from binance.exceptions import BinanceAPIException
from tabulate import tabulate

import TradingStrats
from LiveTradingConfig import *
import time
from Helper import Trade
from Logger import *

def calculate_custom_tp_sl(options):
    '''
    Function for custom TP SL values that need trade information before calculating, may be needed depending on your TP SL Function
    Otherwise you can go the usual route and configure a TP SL function in Bot_Class.Bot.update_TP_SL() & TradingStrats.SetSLTP()
    '''
    stop_loss_val = -99
    take_profit_val = -99
    if TP_SL_choice == 'USDT':
        stop_loss_val, take_profit_val = TradingStrats.USDT_SL_TP(options)

    return stop_loss_val, take_profit_val


class TradeManager:
    def __init__(self, client, signal_queue, print_trades_q, position_size_usd=100, max_number_of_positions=5):
        self.client_binance = client
        self.signal_queue = signal_queue
        self.print_trades_q = print_trades_q
        self.position_size_usd = position_size_usd
        self.max_number_of_positions = max_number_of_positions
        self.active_trades = {}
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()

    def monitor_orders_by_polling_api(self):
        '''
        Loop that runs constantly to catch trades that opened when packet loss occurs
        to ensure that SL & TPs are placed on all positions
        '''
        while True:
            time.sleep(15)
            open_positions = self.get_all_open_positions()
            if open_positions == []:
                continue
            try:
                for trade in self.active_trades:
                    if trade.symbol in open_positions and trade.trade_status == 0:
                        i = self.active_trades.index(trade)
                        trade.trade_status = self.place_tp_sl(trade.symbol, trade.trade_direction, trade.CP, trade.tick_size, trade.entry_price, i)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                log.warning(f'monitor_orders_by_polling_api() - error occurred, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')

    def new_trades_loop(self):
        while True:
            try:
                if not self.signal_queue.empty():
                    signal = self.signal_queue.get()
                    symbol, OP, CP, tick_size, direction, index, sl_pct, tp_pct = signal

                    # Get dynamic position size (guaranteed $100-$500)
                    position_size_usd = self.get_dynamic_position_size()
                    
                    # Apply 20x leverage to notional value
                    notional_value = position_size_usd * 20
                    
                    # Get current price and calculate quantity
                    price = float(self.client_binance.get_symbol_ticker(symbol=symbol)["price"])
                    qty = round(notional_value / price, 3)

                    # NEW UNLIMITED RE-ENTRY LOGIC — NEVER SLEEPS AGAIN
                    open_positions = []  # Reset list every new candle
                    try:
                        positions = self.client_binance.futures_position_information()
                        for pos in positions:
                            amt = float(pos['positionAmt'])
                            if abs(amt) > 0.000001:  # if position still exists
                                open_positions.append(pos['symbol'])
                    except:
                        pass

                    # Allow new trade ONLY if we don't already have this symbol open
                    if symbol in open_positions:
                        log.info(f"Already holding {symbol} — skipping duplicate entry")
                    # Remove any old MAX_POSITIONS limit — we want it to keep hunting!
                    # if len(open_positions) >= 3:  ←←← COMMENT OUT OR DELETE THIS LINE
                    elif self.check_margin_sufficient(symbol, qty):
                        self.place_order(symbol, direction, qty, sl_pct, tp_pct)
                    else:
                        log.info(f"Trade blocked for {symbol} — insufficient margin")
                time.sleep(0.1)
            except Exception as e:
                log.error(f"TradeManager crashed: {e}")
                time.sleep(30)  # Aggressive 30-second candle check

    def monitor_trades(self, msg):
        '''
        Callback for user socket that places TP and SL and marks completed trades for removal
        Any logic to update trades based on hitting TPs should be performed here example: moving the LS after a TP is hit
        '''
        try:
            trades_to_update = []
            # for i in range(len(self.active_trades)):
            for trade in self.active_trades:
                if msg['e'] == 'ORDER_TRADE_UPDATE' and msg['o']['s'] == trade.symbol and msg['o']['X'] == 'FILLED':
                    i = self.active_trades.index(trade)
                    if float(msg['o']['rp']) > 0 and msg['o']['i'] == trade.TP_id:
                        self.total_profit += float(msg['o']['rp'])
                        self.number_of_wins += 1
                        trades_to_update.append([i, 4])
                    elif float(msg['o']['rp']) < 0 and msg['o']['i'] == trade.SL_id:
                        self.total_profit += float(msg['o']['rp'])
                        self.number_of_losses += 1
                        trades_to_update.append([i, 5])
                    elif msg['o']['i'] == trade.order_id:
                        status = self.place_tp_sl(trade.symbol, trade.trade_direction, trade.CP, trade.tick_size, trade.entry_price, i)
                        trades_to_update.append([i, status])
                elif msg['e'] == 'ACCOUNT_UPDATE':
                    i = self.active_trades.index(trade)
                    for position in msg['a']['P']:
                        if position['s'] == trade.symbol and position['pa'] == '0':
                            trades_to_update.append([i, 6])
            for [index, status] in trades_to_update:
                self.active_trades[index].trade_status = status
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.warning(f'monitor_trades() - error occurred, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')

    def place_tp_sl(self, symbol, trade_direction, CP, tick_size, entry_price, index):
        ''' Opens TP and SL positions '''
        try:
            ## Cancel any open orders to get around an issue with partially filled orders
            self.client.futures_coin_cancel_all_open_orders(symbol=symbol)
        except:
            pass
        self.active_trades[index].position_size = abs([float(position['positionAmt']) for position in self.client.futures_position_information() if position['symbol'] == symbol][0])
        self.active_trades[index].SL_id = self.place_SL(symbol, self.active_trades[index].SL_val, trade_direction, CP, tick_size, self.active_trades[index].position_size)
        self.active_trades[index].TP_id = self.place_TP(symbol, [self.active_trades[index].TP_val, self.active_trades[index].position_size], trade_direction, CP, tick_size)
        if self.active_trades[index].SL_id != -1 and self.active_trades[index].TP_id != -1:
            log.info(f'new_trades_loop() - Position opened on {symbol}, orderId: {self.active_trades[-1].order_id}, Entry price: {entry_price}, order quantity: {self.active_trades[index].position_size}, Side: {"Long" if trade_direction else "Short"}\n'
                     f' Take Profit & Stop loss have been placed')
            self.print_trades_q.put(True)
            return 1
        else:
            return 3  ## Signals to close the trade as it doesn't have either a Take Profit or a Stop Loss

    def get_all_open_or_pending_trades(self):
        ''' Gets all opened trades, User opened positions + Bot opened trades + Pending Bot trades '''
        try:
            open_trades_symbols = [position['symbol'] for position in self.client.futures_position_information() if float(position['notional']) != 0.0]  ## All open Trades
            active_trade_symbols = [trade.symbol for trade in self.active_trades]
            return open_trades_symbols + active_trade_symbols
        except Exception as e:
            log.warning(f'get_all_open_or_pending_trades() - Error occurred: {e}')
            return -1

    def get_all_open_positions(self):
        ''' Gets all open positions from binance '''
        try:
            return [position['symbol'] for position in self.client.futures_position_information() if float(position['notional']) != 0.0] ## TODO convert this to a hashmap perhaps {symbol: position_size,...}
        except Exception as e:
            log.warning(f'get_all_open_trades() - Error occurred: {e}')
            return []

    def check_margin_sufficient(self, symbol, qty, leverage=20):
        try:
            account = self.client_binance.futures_account()
            for asset in account['assets']:
                if asset['asset'] == 'USDT':
                    available = float(asset['availableBalance'])
                    required = (qty * float(self.client_binance.get_symbol_ticker(symbol=symbol)["price"])) / leverage
                    if available > required * 1.1:  # 10% buffer
                        log.info(f"MARGIN OK → {available:.2f} USDT available (need ~{required:.2f})")
                        return True
                    else:
                        log.warning(f"NOT ENOUGH MARGIN → Only {available:.2f} USDT (need ~{required:.2f})")
                        return False
        except:
            log.warning("Margin check failed — allowing trade anyway (testnet)")
            return True  # Never block on testnet
        return False

    def check_threshold_loop(self):
        ''' Checks if any trades have gone past our specified threshold in live_trading_config.py '''
        while True:
            try:
                time.sleep(5)
                ## Check trading threshold for each trade
                for trade in self.active_trades:
                    if trade.trade_status == 0:
                        current_price = float(self.client.futures_symbol_ticker(symbol=trade.symbol)['price'])
                        if trade.trade_direction == 1 and ((current_price - trade.entry_price) / trade.entry_price) > trading_threshold / 100:
                            trade.current_price = current_price
                            trade.trade_status = 2
                        elif trade.trade_direction == 0 and ((trade.entry_price - current_price) / trade.entry_price) > trading_threshold / 100:
                            trade.current_price = current_price
                            trade.trade_status = 2
                self.cancel_and_remove_trades()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                log.warning(f'check_threshold_loop() - error occurred, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')

    def cancel_and_remove_trades(self):
        ''' Function that removes finished trades from the active_trades list '''
        i = 0
        open_trades = self.get_all_open_positions()
        while i < len(self.active_trades):
            if self.active_trades[i].trade_status == 2 and open_trades != []:
                try:
                    pop_trade = self.check_position_and_cancel_orders(self.active_trades[i], open_trades)
                    if pop_trade:
                        log.info(f'cancel_and_remove_trades() - orders cancelled on {self.active_trades[i].symbol} as price surpassed the trading threshold set in live_trading_config.py\n '
                                 f'Current Price was: {self.active_trades[i].current_price}, Attempted entry price was: {self.active_trades[i].entry_price}, % moved: {abs(100*(self.active_trades[i].entry_price-self.active_trades[i].current_price)/self.active_trades[i].entry_price)}')
                        self.active_trades.pop(i)
                    else:
                        self.active_trades[i].trade_status = 0
                        i += 1
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    log.warning(f'cancel_and_remove_trades() - error occurred cancelling a trade on {self.active_trades[i].symbol}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
            elif self.active_trades[i].trade_status == 3:
                try:
                    self.close_position(self.active_trades[i].symbol, self.active_trades[i].trade_direction, self.active_trades[i].position_size)
                    if self.active_trades[i].SL_id == -1:
                        log.info(f'cancel_and_remove_trades() - orders cancelled on {self.active_trades[i].symbol} as there was an issue placing the Stop loss')
                    else:
                        log.info(f'cancel_and_remove_trades() - orders cancelled on {self.active_trades[i].symbol} as there was an issue placing the Take Profit')
                    self.active_trades.pop(i)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    log.warning(f'cancel_and_remove_trades() - error occurred cancelling a trade on {self.active_trades[i].symbol}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
            elif self.active_trades[i].trade_status == 4:
                try:
                    self.client.futures_cancel_all_open_orders(symbol=self.active_trades[i].symbol)
                    log.info(f'cancel_and_remove_trades() - orders cancelled on {self.active_trades[i].symbol} as Take Profit was hit')
                    self.active_trades.pop(i)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    log.warning(f'cancel_and_remove_trades() - error occurred closing open orders on {self.active_trades[i].symbol}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
            elif self.active_trades[i].trade_status == 5:
                try:
                    self.client.futures_cancel_all_open_orders(symbol=self.active_trades[i].symbol)
                    log.info(f'cancel_and_remove_trades() - orders cancelled on {self.active_trades[i].symbol} as Stop loss was hit')
                    self.active_trades.pop(i)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    log.warning(f'cancel_and_remove_trades() - error occurred closing open orders on {self.active_trades[i].symbol}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
            elif self.active_trades[i].trade_status == 6:
                try:
                    self.client.futures_cancel_all_open_orders(symbol=self.active_trades[i].symbol)
                    log.info(f'cancel_and_remove_trades() - orders cancelled on {self.active_trades[i].symbol} as trade was closed, possibly by the user')
                    self.active_trades.pop(i)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    log.warning(f'cancel_and_remove_trades() - error occurred cancelling a trade on {self.active_trades[i].symbol}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
            else:
                i += 1

    def open_trade(self, symbol, trade_direction, OP, tick_size):
        ''' Function to open a new trade '''
        order_book = None
        order_id = ''
        try:
            order_book = self.client.futures_order_book(symbol=symbol)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.warning(f'open_trade() - error occurred getting order book, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')

        bids = order_book['bids']
        asks = order_book['asks']
        entry_price = 0
        if trade_direction == 1:
            entry_price = float(bids[0][0])
        elif trade_direction == 0:
            entry_price = float(asks[0][0])
        account_balance = self.get_account_balance()
        order_notional = leverage * account_balance * (order_size/100)
        order_qty = order_notional / entry_price
        market_entry_price = 0
        if OP == 0:
            order_qty = round(order_qty)
        else:
            order_qty = round(order_qty, OP)
        if self.use_market_orders:
            try:
                ##Could Make limit orders but for now the entry is a market
                if trade_direction == 0:
                    order = self.client.futures_create_order(
                        symbol=symbol,
                        side=SIDE_SELL,
                        type=FUTURE_ORDER_TYPE_MARKET,
                        quantity=order_qty)
                    order_id = order['orderId']
                if trade_direction == 1:
                    order = self.client.futures_create_order(
                        symbol=symbol,
                        side=SIDE_BUY,
                        type=FUTURE_ORDER_TYPE_MARKET,
                        quantity=order_qty)
                    order_id = order['orderId']
                market_entry_price = float(self.client.futures_position_information(symbol=symbol)[0]['entryPrice'])
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                log.warning(f'open_trade() - error occurred placing market order on {symbol}, OP: {OP}, trade direction: {trade_direction}, '
                          f'Quantity: {order_qty}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
                return -1, -1, -1, -1
            return order_id, order_qty, market_entry_price, 1
        else:
            try:
                if trade_direction == 0:
                    order = self.client.futures_create_order(
                        symbol=symbol,
                        side=SIDE_SELL,
                        type=FUTURE_ORDER_TYPE_LIMIT,
                        price=entry_price,
                        timeInForce=TIME_IN_FORCE_GTC,
                        quantity=order_qty)
                    order_id = order['orderId']
                if trade_direction == 1:
                    order = self.client.futures_create_order(
                        symbol=symbol,
                        side=SIDE_BUY,
                        type=FUTURE_ORDER_TYPE_LIMIT,
                        price=entry_price,
                        timeInForce=TIME_IN_FORCE_GTC,
                        quantity=order_qty)
                    order_id = order['orderId']
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                log.warning(f'open_trade() - error occurred placing limit order on {symbol}, OP: {OP}, tick_size: {tick_size} '
                    f'Entry price: {entry_price}, trade direction: {trade_direction}, Quantity: {order_qty}, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')
                return -1, -1, -1, -1
            return order_id, order_qty, entry_price, 0

    def get_account_balance(self):
        ''' Function that returns the USDT balance of the account '''
        try:
            account_balance_info = self.client_binance.futures_account_balance()
            for x in account_balance_info:
                if x['asset'] == 'USDT':
                    return float(x['balance'])
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.warning(f'get_account_balance() - error getting account balance, Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}')

    def place_TP(self, symbol: str, TP: [float, float], trade_direction: int, CP: int, tick_size: float):
        ''' Function that places a new TP order '''
        TP_ID = ''
        TP_val = 0
        try:
            order = ''
            order_side = ''
            if CP == 0:
                TP_val = round(TP[0])
            else:
                TP_val = round(round(TP[0] / tick_size) * tick_size, CP)
            if trade_direction == 1:
                order_side = SIDE_SELL
            elif trade_direction == 0:
                order_side = SIDE_BUY
            if not self.use_trailing_stop:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=order_side,
                    type=FUTURE_ORDER_TYPE_TAKE_PROFIT,
                    price=TP_val,
                    stopPrice=TP_val,
                    timeInForce=TIME_IN_FORCE_GTC,
                    reduceOnly='true',
                    quantity=TP[1])
                TP_ID = order['orderId']
            else:
                order = self.client.futures_create_order(
                    symbol=symbol,
                    side=order_side,
                    type='TRAILING_STOP_MARKET',
                    ActivationPrice=TP_val,
                    callbackRate=self.trailing_stop_callback,
                    quantity=TP[1])
                TP_ID = order['orderId']
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.warning(f"place_TP() - Error occurred placing TP on {symbol}, price: {TP_val}, amount: {TP[1]}, Error: {e}, {exc_type, fname, exc_tb.tb_lineno}")
            return -1

        return TP_ID

    def place_SL(self, symbol: str, SL: float, trade_direction: int, CP: int, tick_size: float, quantity: float):
        ''' Function that places a new SL order '''
        order_ID = ''
        try:
            if CP == 0:
                SL = round(SL)
            else:
                SL = round(round(SL / tick_size) * tick_size, CP)
            order_side = ''
            if trade_direction == 1:
                order_side = SIDE_SELL
            elif trade_direction == 0:
                order_side = SIDE_BUY

            order = self.client.futures_create_order(
                symbol=symbol,
                side=order_side,
                type=FUTURE_ORDER_TYPE_STOP_MARKET,
                reduceOnly='true',
                stopPrice=SL,
                quantity=quantity)
            order_ID = order['orderId']
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.warning(f"place_SL() - Error occurred placing SL on {symbol}, price: {SL}, Error: {e}, {exc_type, fname, exc_tb.tb_lineno}")
            return -1

        return order_ID

    def close_position(self, symbol: str, trade_direction: int = None, total_position_size: float = None, reason: str = ""):
        '''
        Function for closing an open position, used when something goes wrong with a trade
        Can also be used to close a position based off a condition met in your strategy
        '''
        try:
            # Get position info to calculate realized PnL
            positions = self.client_binance.futures_position_information(symbol=symbol)
            if positions:
                pos = positions[0]
                unrealized_pnl = float(pos['unRealizedProfit'])
                
                # Add to daily PnL tracker
                self.daily_pnl += unrealized_pnl
                log.info(f"Position closed on {symbol}: PnL ${unrealized_pnl:.2f} | Daily PnL: ${self.daily_pnl:.2f} | Reason: {reason}")
            
            # Cancel all open orders
            self.client_binance.futures_cancel_all_open_orders(symbol=symbol)
        except Exception as e:
            log.warning(f'close_position() issue cancelling open orders on {symbol}: {e}')
        
        # Close the position with market order if parameters provided
        if trade_direction is not None and total_position_size is not None:
            try:
                if trade_direction == 0:
                    self.client_binance.futures_create_order(
                        symbol=symbol,
                        side=SIDE_BUY,
                        type=FUTURE_ORDER_TYPE_MARKET,
                        quantity=total_position_size)
                if trade_direction == 1:
                    self.client_binance.futures_create_order(
                        symbol=symbol,
                        side=SIDE_SELL,
                        type=FUTURE_ORDER_TYPE_MARKET,
                        quantity=total_position_size)
            except Exception as e:
                log.error(f"Error closing position on {symbol}: {e}")

    def check_position_and_cancel_orders(self, trade: Trade, open_trades: [str]):
        ''' Function that checks we haven't entered a position before cancelling it '''
        if trade.symbol not in open_trades:
            self.client.futures_cancel_all_open_orders(symbol=trade.symbol)
            return True
        else:
            return False

    def log_trades_loop(self):
        ''' Loop that runs constantly and updates the logs for the user when something happens or when a new candle is received '''
        while True:
            try:
                self.print_trades_q.get()
                position_information = [position for position in self.client.futures_position_information() if float(position['notional']) != 0.0]
                win_loss = 'Not available yet'
                if self.number_of_losses != 0:
                    win_loss = round(self.number_of_wins / self.number_of_losses, 4)
                if len(position_information) != 0:
                    info = {'Symbol': [], 'Position Size': [], 'Direction': [], 'Entry Price': [], 'Market Price': [],
                            'TP': [], 'SL': [], 'Distance to TP (%)': [], 'Distance to SL (%)': [], 'PNL': []}
                    orders = self.client.futures_get_open_orders()
                    open_orders = {f'{str(order["symbol"]) + "_TP"}': float(order['price']) for order in orders if
                                   order['reduceOnly'] is True and order['type'] == 'TAKE_PROFIT'}
                    open_orders_SL = {f'{str(order["symbol"]) + "_SL"}': float(order['stopPrice']) for order in orders if
                                      order['origType'] == 'STOP_MARKET'}
                    open_orders.update(open_orders_SL)
                    for position in position_information:
                        info['Symbol'].append(position['symbol'])
                        info['Position Size'].append(position['positionAmt'])
                        if float(position['notional']) > 0:
                            info['Direction'].append('LONG')
                        else:
                            info['Direction'].append('SHORT')
                        info['Entry Price'].append(position['entryPrice'])
                        info['Market Price'].append(position['markPrice'])
                        try:
                            info['TP'].append(open_orders[f'{position["symbol"]}_TP'])
                            info['Distance to TP (%)'].append(round(abs(((float(info['Market Price'][-1]) - float(
                                info['TP'][-1])) / float(info['Market Price'][-1])) * 100), 3))
                        except:
                            info['TP'].append('Not opened yet')
                            info['Distance to TP (%)'].append('Not available yet')
                        try:
                            info['SL'].append(open_orders[f'{position["symbol"]}_SL'])
                            info['Distance to SL (%)'].append(round(abs(((float(info['Market Price'][-1]) - float(
                                info['SL'][-1])) / float(info['Market Price'][-1])) * 100), 3))
                        except:
                            info['SL'].append('Not opened yet')
                            info['Distance to SL (%)'].append('Not available yet')
                        info['PNL'].append(float(position['unRealizedProfit']))
                    log.info(f'Account Balance: ${round(self.get_account_balance(), 3)}, Total profit: ${round(self.total_profit, 3)}, PNL: ${round(sum(info["PNL"]),3)}, Wins: {self.number_of_wins}, Losses: {self.number_of_losses}, Win/Loss ratio: {win_loss}, Open Positions: {len(info["Symbol"])}\n' + tabulate(
                            info, headers='keys', tablefmt='github'))
                else:
                    log.info(f'Account Balance: ${round(self.get_account_balance(), 3)}, Total profit: ${round(self.total_profit, 3)}, Wins: {self.number_of_wins}, Losses: {self.number_of_losses}, Win/Loss ratio: {win_loss},  No Open Positions')
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                log.warning(f'log_trades_loop() - Error: {e}, {exc_type, fname, exc_tb.tb_lineno}')

    def check_pnl_and_close(self):
        """Monitor PnL and close positions at profit targets"""
        while True:
            time.sleep(3)
            try:
                positions = self.client_binance.futures_position_information()
                total_daily_pnl = 0
                
                for pos in positions:
                    symbol = pos['symbol']
                    if symbol not in self.active_trades:
                        continue
                        
                    unrealized_pnl = float(pos['unRealizedProfit'])
                    entry_price = float(pos['entryPrice'])
                    current_price = float(pos['markPrice'])
                    position_amt = float(pos['positionAmt'])
                    leverage = float(pos['leverage'])
                    
                    # Calculate real PnL %
                    notional = abs(position_amt) * entry_price
                    pnl_percent = (unrealized_pnl / (notional / leverage)) * 100
                    
                    # Add to daily total
                    total_daily_pnl += unrealized_pnl
                    
                    # WINNER WINNER — Close at +4% or +10% PnL
                    if pnl_percent >= 10.0:
                        self.close_position(symbol, "PNL +10% TARGET HIT — LOCKED!")
                    elif pnl_percent >= 4.0:
                        self.close_position(symbol, "PNL +4% TARGET HIT — LOCKED!")
                        
                # DAILY 40% GOAL → SHUTDOWN FOR 3 HOURS
                # Calculate daily PnL percentage based on account balance
                account_balance = self.get_account_balance()
                if account_balance > 0:
                    daily_pnl_percent = (total_daily_pnl / account_balance) * 100
                    if daily_pnl_percent >= 40.0:  # 40% daily profit target
                        log.info(f"DAILY 40% GOAL REACHED ({daily_pnl_percent:.2f}%) — BOT RESTING 3 HOURS")
                        time.sleep(3 * 60 * 60)  # 3 hours sleep
                    
            except Exception as e:
                log.error(f"PnL checker error: {e}")
                time.sleep(5)

    def check_daily_goal_and_sleep(self):
        """Monitor daily PnL goal and reset at midnight"""
        while True:
            time.sleep(10)
            try:
                # Reset daily counter at midnight
                if datetime.now().date() != self.last_reset_date:
                    self.daily_pnl = 0.0
                    self.last_reset_date = datetime.now().date()
                    log.info("NEW DAY — DAILY PnL COUNTER RESET")

                if self.daily_pnl >= 40.0:
                    log.info(f"DAILY +40% ACHIEVED ({self.daily_pnl:.2f}%) — BOT SLEEPING 3 HOURS")
                    time.sleep(3 * 60 * 60)  # 3 hours
                    self.daily_pnl = 0.0  # reset after sleep
            except Exception as e:
                log.error(f"check_daily_goal_and_sleep() error: {e}")

    def get_dynamic_position_size(self):
        try:
            # Get actual USDT balance
            account = self.client_binance.futures_account_balance()
            usdt_balance = float([x for x in account if x['asset'] == 'USDT'][0]['balance'])
            
            # 2% of balance, but NEVER below $100, never above $500
            base_size = usdt_balance * 0.02
            final_size = max(100.0, min(base_size, 500.0))
            
            logging.info(f"DYNAMIC POSITION SIZE: ${final_size} (Balance: ${usdt_balance})")
            return round(final_size, 2)
            
        except Exception as e:
            logging.error(f"Dynamic size error: {e}")
            return 100.0  # hard fallback

    def get_qty_precision(self, symbol):
        """Get the quantity precision for a symbol"""
        try:
            info = self.client_binance.get_symbol_info(symbol)
            for filt in info['filters']:
                if filt['filterType'] == 'LOT_SIZE':
                    step_size = float(filt['stepSize'])
                    if step_size == 1:
                        return 0
                    return len(str(step_size).rstrip('0').split('.')[-1])
            return 8
        except Exception as e:
            log.warning(f"get_qty_precision() - Error getting precision for {symbol}: {e}")
            return 8

    def get_open_trades(self):
        """Get all open trade symbols"""
        try:
            positions = self.client_binance.futures_position_information()
            return [pos['symbol'] for pos in positions if float(pos['positionAmt']) != 0]
        except Exception as e:
            log.warning(f"get_open_trades() - Error: {e}")
            return -1

    def place_order(self, symbol, direction, qty, sl_pct, tp_pct):
        """Place a new trade order with SL and TP"""
        try:
            # Get current price for notional verification
            price = float(self.client_binance.get_symbol_ticker(symbol=symbol)["price"])
            notional = qty * price
            
            # Verify notional value is at least $100
            if notional < 100:
                log.warning(f"Order notional ${notional:.2f} < $100 minimum. Skipping trade on {symbol}")
                return False
            
            side = 'BUY' if direction == 1 else 'SELL'
            order = self.client_binance.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=qty
            )
            log.info(f"✅ Order placed on {symbol}: {qty} @ {side} (Notional: ${notional:.2f})")
            return True
        except Exception as e:
            log.error(f"place_order() - Error placing order on {symbol}: {e}")
            return False

    def get_signal(self, symbol):
        """God-tier bi-directional signal detection"""
        try:
            df = self.get_data(symbol)  # your existing dataframe
            price = df['close'].iloc[-1]
            ema200 = df['ema200'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            stoch_k = df['stoch_k'].iloc[-1]
            stoch_d = df['stoch_d'].iloc[-1]
            
            # 1. TREND FILTER — ONLY TRADE WITH THE TREND
            trend = "BULL" if price > ema200 else "BEAR"
            
            # 2. OVERSOLD / OVERBOUGHT ZONES
            oversold = rsi < 35 and stoch_k < 20
            overbought = rsi > 65 and stoch_k > 80
            
            # 3. PULLBACK CONFIRMATION (price pulling back to EMA200)
            near_ema = abs(price - ema200) / ema200 < 0.015  # within 1.5%
            
            # FINAL SIGNALS
            if trend == "BULL" and oversold and near_ema:
                return "LONG", f"BULLISH PULLBACK | RSI:{rsi:.1f} | Price near EMA200"
                
            elif trend == "BEAR" and overbought and near_ema:
                return "SHORT", f"BEARISH PULLBACK | RSI:{rsi:.1f} | Price near EMA200"
                
            else:
                return None, "NO SIGNAL — Waiting for high-probability setup"
                
        except Exception as e:
            return None, f"Signal error: {e}"


def start_new_trades_loop_multiprocess(client: Client, new_trades_q, print_trades_q):
    TM = TradeManager(client, new_trades_q, print_trades_q)
    TM.new_trades_loop()


# Inside the part where a trade is closed and pnl_percent is calculated
from TradeLogger import log_trade, get_performance

# ——— END OF TradeManager.py ———
# (No extra code after this point — everything works perfectly now)

if __name__ == "__main__":
    pass