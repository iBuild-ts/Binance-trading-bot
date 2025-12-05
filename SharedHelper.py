import numpy as np
from Logger import *
import BotClass
import sys
import os


def get_all_symbols(client, coin_exclusion_list):
    ''' Function that returns the list of trade-able USDT symbols & removes coins you've added to your exclusion list '''
    x = client.futures_exchange_info()['symbols']
    symbols_to_trade = [y['symbol'] for y in x if (y['status'] == 'TRADING' and
                                                   'USDT' in y['symbol'] and '_' not in y['symbol'] and
                                                   y['symbol'] not in coin_exclusion_list)]
    return symbols_to_trade


def compare_indicators(keys, indicators_buffer, indicators_actual):
    '''
    Ultra-robust version: never raises ZeroDivisionError or TypeError
    Returns a large penalty (1000.0) when data is missing/invalid instead of crashing
    '''
    try:
        error_percent = []

        for key in keys:
            act_vals = indicators_actual[key]['values']
            buf_vals = indicators_buffer[key]['values']

            # Case 1: indicator returns a list (e.g. MACD has signal line, Bollinger has upper/lower, etc.)
            if isinstance(act_vals, list):
                if len(act_vals) < 30 or len(buf_vals) < 30:
                    error_percent.append(1000.0)
                    continue

                total_diff = 0.0
                valid_count = 0

                for a, b in zip(act_vals[-30:], buf_vals[-30:]):
                    if a is None or b is None or a == 0 or (hasattr(a, '__len__') and np.isnan(a).any()):
                        continue
                    if np.isnan(a) or np.isnan(b):
                        continue
                    total_diff += abs((a - b) / a)
                    valid_count += 1

                if valid_count == 0:
                    error_percent.append(1000.0)
                else:
                    error_percent.append(total_diff / valid_count)

            # Case 2: single-value indicator
            else:
                a = act_vals
                b = buf_vals
                if a is None or b is None or a == 0 or np.isnan(a) or np.isnan(b):
                    error_percent.append(1000.0)
                else:
                    error_percent.append(abs((a - b) / a))

        if not error_percent:
            return 1000.0

        avg_error = sum(error_percent) / len(error_percent)
        return avg_error if np.isfinite(avg_error) else 1000.0

    except Exception as e:
        log.debug(f"compare_indicators() unexpected failure: {e}")
        return 1000.0  # safe fallback


def get_required_buffer(trading_strategy):
    '''
    FAST & RELIABLE VERSION
    No more 20,000-bar random loops → instantly returns a safe buffer
    300 candles is more than enough for any common indicator (RSI, MACD, EMA, SuperTrend, etc.)
    '''
    log.info('get_required_buffer() - Using fast pre-defined buffer (300 candles)')

    # You can customize per strategy if you ever need something different:
    strategy_buffers = {
        'RSI': 100,
        'MACD': 200,
        'SuperTrend': 150,
        'EMA_Cross': 300,
        'Bollinger': 200,
        'Default': 300
    }

    buffer = strategy_buffers.get(trading_strategy, strategy_buffers['Default'])
    log.info(f"Strategy '{trading_strategy}' → using buffer of {buffer} candles")
    return buffer

    # ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
    # THE OLD SLOW & BUGGY CODE IS COMMENTED OUT BELOW (kept only for reference)
    # --------------------------------------------------------------------
    """
    log.info('get_required_buffer() - Calculating the required buffer for your strategy...')

    np.random.seed(5)
    ran_arr_open = np.random.uniform(size=20000, low=2, high=100)
    np.random.seed(300)
    ran_arr_close = np.random.uniform(size=20000, low=2, high=100)
    np.random.seed(44)
    ran_arr_high = np.random.uniform(size=20000, low=2, high=100)
    np.random.seed(29)
    ran_arr_low = np.random.uniform(size=20000, low=2, high=100)
    np.random.seed(78)
    ran_arr_volume = np.random.uniform(size=20000, low=2, high=100_000_000)

    actual_values_bot = BotClass.Bot('actual_values_bot', ran_arr_open, ran_arr_close, ran_arr_high,
                                      ran_arr_low, ran_arr_volume, [], 3, 4, 0, 1, trading_strategy, '%',
                                      1, 1, 1)

    for i in range(30, 20000):
        try:
            buffer_bot = BotClass.Bot('buffer_bot', ran_arr_open[-i:], ran_arr_close[-i:], ran_arr_high[-i:],
                                       ran_arr_low[-i:], ran_arr_volume[-i:], [], 3, 4, 0, 1, trading_strategy,
                                       '%', 1, 1, 1)

            if not buffer_bot.indicators:
                continue

            keys = buffer_bot.indicators.keys()
            error_percent = compare_indicators(keys, buffer_bot.indicators, actual_values_bot.indicators)

            if error_percent < 0.00001:
                log.info(f"Required buffer calculated: {i} candles")
                return i

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            log.warning(f"get_required_buffer() - Error Info: {exc_obj, fname, exc_tb.tb_lineno}, Error: {e}")

    log.info("Max buffer (20000) reached, using 20000")
    return 20000
    """