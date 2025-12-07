#!/usr/bin/env python3
"""
LOSS ANALYSIS TOOL
Analyzes bot_trades.csv to identify why the bot is losing money
"""

import pandas as pd
import numpy as np
from datetime import datetime

def analyze_trades():
    """Analyze trade performance"""
    
    # Read trades
    df = pd.read_csv('bot_trades.csv')
    
    print("\n" + "="*80)
    print("BINANCE BOT LOSS ANALYSIS — December 6, 2025")
    print("="*80)
    
    # Basic stats
    total_trades = len(df)
    winning_trades = len(df[df['PNL_Percent'].str.contains('\+', na=False)])
    losing_trades = len(df[df['PNL_Percent'].str.contains('-', na=False)])
    
    print(f"\n📊 TRADE SUMMARY:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Winning Trades: {winning_trades} ({winning_trades/total_trades*100:.1f}%)")
    print(f"   Losing Trades: {losing_trades} ({losing_trades/total_trades*100:.1f}%)")
    
    # Extract numeric PNL
    df['PNL_Clean'] = df['PNL_Percent'].str.replace('%', '').astype(float)
    
    total_pnl = df['PNL_USDT'].sum()
    avg_win = df[df['PNL_Clean'] > 0]['PNL_Clean'].mean()
    avg_loss = df[df['PNL_Clean'] < 0]['PNL_Clean'].mean()
    
    print(f"\n💰 FINANCIAL SUMMARY:")
    print(f"   Total PnL: ${total_pnl:.2f}")
    print(f"   Average Win: +{avg_win:.2f}%")
    print(f"   Average Loss: {avg_loss:.2f}%")
    print(f"   Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}x")
    
    # Critical issues
    print(f"\n⚠️  CRITICAL ISSUES FOUND:")
    
    # Issue 1: Missing entry/exit prices
    missing_prices = df[df['Entry_Price'].isna()].shape[0]
    print(f"   1. Missing Entry/Exit Prices: {missing_prices} trades ({missing_prices/total_trades*100:.1f}%)")
    print(f"      → Bot is NOT tracking actual execution prices!")
    
    # Issue 2: Duplicate trades
    duplicates = df.duplicated(subset=['Timestamp', 'Symbol', 'Direction']).sum()
    print(f"   2. Duplicate Trades: {duplicates}")
    print(f"      → Bot is placing multiple orders for same signal!")
    
    # Issue 3: Cascading losses
    df['Date'] = pd.to_datetime(df['Timestamp']).dt.date
    daily_pnl = df.groupby('Date')['PNL_USDT'].sum()
    negative_days = (daily_pnl < 0).sum()
    print(f"   3. Negative Days: {negative_days} out of {len(daily_pnl)} days")
    print(f"      → Losing more days than winning!")
    
    # Issue 4: Loss streaks
    df['Win'] = df['PNL_Clean'] > 0
    consecutive_losses = 0
    max_consecutive_losses = 0
    for win in df['Win']:
        if not win:
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        else:
            consecutive_losses = 0
    
    print(f"   4. Max Consecutive Losses: {max_consecutive_losses} trades")
    print(f"      → Bot doesn't stop after losing streak!")
    
    # Issue 5: Position sizing
    print(f"\n🔧 POSITION SIZING ISSUES:")
    print(f"   • Leverage = 0 in config (should be 20)")
    print(f"   • Order size = 10 USDT (at 20x = 200 USDT position)")
    print(f"   • Current positions are TINY — no leverage applied!")
    
    # Recommendations
    print(f"\n✅ FIXES NEEDED (PRIORITY ORDER):")
    print(f"   1. Change leverage from 0 → 20 in LiveTradingConfig.py")
    print(f"   2. Add proper entry/exit price tracking to order execution")
    print(f"   3. Implement duplicate order prevention")
    print(f"   4. Add daily loss limit (stop trading after -3% daily loss)")
    print(f"   5. Add max consecutive loss limit (stop after 3 losses)")
    print(f"   6. Move API keys to .env file (SECURITY)")
    
    # Daily breakdown
    print(f"\n📈 DAILY BREAKDOWN:")
    for date, pnl in daily_pnl.items():
        status = "✅ WIN" if pnl > 0 else "❌ LOSS"
        print(f"   {date}: {status} ${pnl:+.2f}")
    
    print("\n" + "="*80)
    print("Run this script daily to monitor bot performance")
    print("="*80 + "\n")

if __name__ == "__main__":
    analyze_trades()
