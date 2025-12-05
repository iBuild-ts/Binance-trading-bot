import csv
from datetime import datetime
import os

LOG_FILE = "trade_history.csv"

def log_trade(symbol, side, entry_price, qty, exit_price=None, pnl=None):
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "Symbol", "Side", "Entry", "Qty", "Exit", "P&L %", "P&L $"])
        pnl_percent = round(((exit_price/entry_price - 1) * 100 if side == "LONG" else (1 - exit_price/entry_price) * 100), 2) if exit_price else 0
        pnl_usd = round(pnl_percent/100 * entry_price * qty, 2) if exit_price else 0
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), symbol, side, entry_price, qty, exit_price or "", f"{pnl_percent}%", f"${pnl_usd}"])

def get_performance():
    if not os.path.isfile(LOG_FILE):
        return "No trades yet"
    import pandas as pd
    df = pd.read_csv(LOG_FILE)
    total_pnl = df['P&L $'].sum().round(2)
    win_rate = len(df[df['P&L %'] > 0]) / len(df) * 100 if len(df) > 0 else 0
    return f"Total P&L: ${total_pnl} | Win Rate: {win_rate:.1f}% | Trades: {len(df)}"