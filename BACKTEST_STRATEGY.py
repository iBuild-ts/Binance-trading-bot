#!/usr/bin/env python3
"""
BACKTEST_STRATEGY.py
Backtest the enhanced strategy on historical data
Calculates win rate, profit factor, and performance metrics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from ENHANCED_STRATEGY import enhanced_momentum_strategy

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

class StrategyBacktester:
    """Backtest trading strategy on historical data"""
    
    def __init__(self, initial_balance=10000, risk_per_trade=2.0, min_signal_strength=60):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.min_signal_strength = min_signal_strength
        self.trades = []
        self.equity_curve = [initial_balance]
        
    def calculate_position_size(self, entry_price, stop_loss_price):
        """Calculate position size based on risk"""
        risk_amount = self.current_balance * (self.risk_per_trade / 100)
        price_difference = abs(entry_price - stop_loss_price)
        
        if price_difference == 0:
            return 0
        
        position_size = risk_amount / price_difference
        return position_size
    
    def backtest(self, df, symbol='BTCUSDT', take_profit_percent=10.3, stop_loss_percent=8.0):
        """
        Backtest strategy on historical data
        df: DataFrame with OHLCV data
        """
        
        logger.info(f"\n{'='*70}")
        logger.info(f"BACKTESTING {symbol}")
        logger.info(f"{'='*70}")
        logger.info(f"Initial Balance: ${self.initial_balance:.2f}")
        logger.info(f"Risk Per Trade: {self.risk_per_trade}%")
        logger.info(f"Min Signal Strength: {self.min_signal_strength}%")
        
        active_trade = None
        
        for idx in range(50, len(df)):
            current_price = df['close'].iloc[idx]
            
            # Check if we should close active trade
            if active_trade:
                entry_price = active_trade['entry_price']
                direction = active_trade['direction']
                entry_idx = active_trade['entry_idx']
                
                # Calculate P&L
                if direction == 1:  # LONG
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    hit_tp = current_price >= active_trade['take_profit']
                    hit_sl = current_price <= active_trade['stop_loss']
                else:  # SHORT
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100
                    hit_tp = current_price <= active_trade['take_profit']
                    hit_sl = current_price >= active_trade['stop_loss']
                
                # Close trade if TP or SL hit
                if hit_tp or hit_sl:
                    exit_reason = "TP" if hit_tp else "SL"
                    exit_price = active_trade['take_profit'] if hit_tp else active_trade['stop_loss']
                    
                    # Calculate PnL
                    pnl_usdt = (active_trade['quantity'] * (exit_price - entry_price)) if direction == 1 else (active_trade['quantity'] * (entry_price - exit_price))
                    
                    # Update balance
                    self.current_balance += pnl_usdt
                    
                    # Record trade
                    trade_record = {
                        'entry_idx': entry_idx,
                        'exit_idx': idx,
                        'symbol': symbol,
                        'direction': 'LONG' if direction == 1 else 'SHORT',
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'quantity': active_trade['quantity'],
                        'pnl_usdt': pnl_usdt,
                        'pnl_pct': pnl_pct,
                        'exit_reason': exit_reason,
                        'signal_strength': active_trade['signal_strength']
                    }
                    self.trades.append(trade_record)
                    
                    logger.info(f"[{idx}] CLOSED {trade_record['direction']} @ {exit_price:.2f} | PnL: {pnl_pct:+.2f}% (${pnl_usdt:+.2f}) | Balance: ${self.current_balance:.2f}")
                    
                    active_trade = None
            
            # Check for new signal
            if not active_trade:
                direction, signal_strength, reasons = enhanced_momentum_strategy(
                    df.iloc[:idx+1].reset_index(drop=True),
                    current_idx=idx,
                    symbol=symbol,
                    min_signal_strength=self.min_signal_strength
                )
                
                if direction != 0:
                    # Calculate position size
                    stop_loss_price = current_price * (1 - stop_loss_percent/100) if direction == 1 else current_price * (1 + stop_loss_percent/100)
                    quantity = self.calculate_position_size(current_price, stop_loss_price)
                    
                    if quantity > 0:
                        # Calculate take profit
                        risk = abs(current_price - stop_loss_price)
                        take_profit_price = current_price + (risk * 2.0) if direction == 1 else current_price - (risk * 2.0)
                        
                        active_trade = {
                            'entry_idx': idx,
                            'entry_price': current_price,
                            'direction': direction,
                            'quantity': quantity,
                            'stop_loss': stop_loss_price,
                            'take_profit': take_profit_price,
                            'signal_strength': signal_strength
                        }
                        
                        logger.info(f"[{idx}] OPENED {'LONG' if direction == 1 else 'SHORT'} @ {current_price:.2f} | Strength: {signal_strength:.1f}% | SL: {stop_loss_price:.2f} | TP: {take_profit_price:.2f}")
            
            # Record equity
            self.equity_curve.append(self.current_balance)
        
        # Close any remaining trade at last price
        if active_trade:
            exit_price = df['close'].iloc[-1]
            direction = active_trade['direction']
            entry_price = active_trade['entry_price']
            
            pnl_usdt = (active_trade['quantity'] * (exit_price - entry_price)) if direction == 1 else (active_trade['quantity'] * (entry_price - exit_price))
            pnl_pct = ((exit_price - entry_price) / entry_price * 100) if direction == 1 else ((entry_price - exit_price) / entry_price * 100)
            
            self.current_balance += pnl_usdt
            
            trade_record = {
                'entry_idx': active_trade['entry_idx'],
                'exit_idx': len(df) - 1,
                'symbol': symbol,
                'direction': 'LONG' if direction == 1 else 'SHORT',
                'entry_price': entry_price,
                'exit_price': exit_price,
                'quantity': active_trade['quantity'],
                'pnl_usdt': pnl_usdt,
                'pnl_pct': pnl_pct,
                'exit_reason': 'END',
                'signal_strength': active_trade['signal_strength']
            }
            self.trades.append(trade_record)
    
    def print_results(self):
        """Print backtest results"""
        
        if not self.trades:
            logger.info("\n❌ No trades executed")
            return
        
        trades_df = pd.DataFrame(self.trades)
        
        # Calculate metrics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl_pct'] > 0])
        losing_trades = len(trades_df[trades_df['pnl_pct'] < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if losing_trades > 0 else 0
        
        total_pnl = trades_df['pnl_pct'].sum()
        total_pnl_usdt = trades_df['pnl_usdt'].sum()
        
        profit_factor = abs(trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].sum() / trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].sum()) if losing_trades > 0 else 0
        
        max_drawdown = self._calculate_max_drawdown()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"BACKTEST RESULTS")
        logger.info(f"{'='*70}")
        logger.info(f"\n📊 TRADE STATISTICS:")
        logger.info(f"   Total Trades: {total_trades}")
        logger.info(f"   Winning Trades: {winning_trades} ({win_rate:.1f}%)")
        logger.info(f"   Losing Trades: {losing_trades} ({100-win_rate:.1f}%)")
        logger.info(f"\n💰 PROFIT METRICS:")
        logger.info(f"   Total PnL: {total_pnl:+.2f}%")
        logger.info(f"   Total PnL (USD): ${total_pnl_usdt:+.2f}")
        logger.info(f"   Average Win: {avg_win:+.2f}%")
        logger.info(f"   Average Loss: {avg_loss:+.2f}%")
        logger.info(f"   Profit Factor: {profit_factor:.2f}x")
        logger.info(f"\n📈 RISK METRICS:")
        logger.info(f"   Max Drawdown: {max_drawdown:.2f}%")
        logger.info(f"   Initial Balance: ${self.initial_balance:.2f}")
        logger.info(f"   Final Balance: ${self.current_balance:.2f}")
        logger.info(f"   Return: {(self.current_balance - self.initial_balance) / self.initial_balance * 100:.2f}%")
        
        logger.info(f"\n{'='*70}")
        logger.info(f"TOP 5 WINNING TRADES:")
        logger.info(f"{'='*70}")
        top_wins = trades_df.nlargest(5, 'pnl_pct')
        for idx, trade in top_wins.iterrows():
            logger.info(f"   {trade['direction']} @ {trade['entry_price']:.2f} → {trade['exit_price']:.2f} | +{trade['pnl_pct']:.2f}%")
        
        logger.info(f"\n{'='*70}")
        logger.info(f"TOP 5 LOSING TRADES:")
        logger.info(f"{'='*70}")
        top_losses = trades_df.nsmallest(5, 'pnl_pct')
        for idx, trade in top_losses.iterrows():
            logger.info(f"   {trade['direction']} @ {trade['entry_price']:.2f} → {trade['exit_price']:.2f} | {trade['pnl_pct']:.2f}%")
        
        # Save results
        trades_df.to_csv('backtest_results.csv', index=False)
        logger.info(f"\n✅ Results saved to backtest_results.csv")
    
    def _calculate_max_drawdown(self):
        """Calculate maximum drawdown"""
        equity = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max * 100
        return np.min(drawdown)

# ================== EXAMPLE USAGE ==================

if __name__ == "__main__":
    # Example: Load historical data and backtest
    # You would normally load this from Binance API or CSV file
    
    logger.info("📊 STRATEGY BACKTEST TOOL")
    logger.info("To use this tool:")
    logger.info("1. Load historical OHLCV data into a DataFrame")
    logger.info("2. Create a StrategyBacktester instance")
    logger.info("3. Call backtest() with your data")
    logger.info("4. Call print_results() to see performance")
    logger.info("\nExample:")
    logger.info("  backtester = StrategyBacktester(initial_balance=10000)")
    logger.info("  backtester.backtest(df, symbol='BTCUSDT')")
    logger.info("  backtester.print_results()")
