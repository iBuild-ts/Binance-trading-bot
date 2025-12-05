"""
TRADE ANALYTICS DASHBOARD
Analyzes bot_trades.csv and generates daily/weekly/monthly reports
Exports to Excel with formatting
"""

import pandas as pd
import os
from datetime import datetime, timedelta

TRADES_CSV = 'bot_trades.csv'
EXCEL_OUTPUT = 'bot_trades_analytics.xlsx'

def load_trades():
    """Load trades from CSV"""
    if not os.path.exists(TRADES_CSV):
        print(f"❌ {TRADES_CSV} not found. Run the bot first to generate trades.")
        return pd.DataFrame()
    
    df = pd.read_csv(TRADES_CSV)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df['PNL_Percent'] = df['PNL_Percent'].str.rstrip('%').astype(float)
    return df

def calculate_stats(trades_df):
    """Calculate trading statistics"""
    if trades_df.empty:
        return None
    
    total_trades = len(trades_df)
    winning_trades = len(trades_df[trades_df['PNL_Percent'] > 0])
    losing_trades = len(trades_df[trades_df['PNL_Percent'] < 0])
    
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    total_pnl = trades_df['PNL_USDT'].sum()
    avg_pnl = trades_df['PNL_USDT'].mean()
    avg_win = trades_df[trades_df['PNL_Percent'] > 0]['PNL_USDT'].mean() if winning_trades > 0 else 0
    avg_loss = trades_df[trades_df['PNL_Percent'] < 0]['PNL_USDT'].mean() if losing_trades > 0 else 0
    
    return {
        'Total Trades': total_trades,
        'Winning Trades': winning_trades,
        'Losing Trades': losing_trades,
        'Win Rate %': f"{win_rate:.2f}%",
        'Total PNL $': f"{total_pnl:.2f}",
        'Avg PNL/Trade $': f"{avg_pnl:.2f}",
        'Avg Win $': f"{avg_win:.2f}",
        'Avg Loss $': f"{avg_loss:.2f}",
        'Profit Factor': f"{abs(avg_win / avg_loss):.2f}" if avg_loss != 0 else "N/A"
    }

def print_stats(stats, period_name):
    """Print statistics in table format"""
    if not stats:
        print(f"\n❌ No trades in {period_name}")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 {period_name.upper()} STATISTICS")
    print(f"{'='*60}")
    for key, value in stats.items():
        print(f"{key:.<40} {value:>15}")

def analyze_daily():
    """Analyze daily performance"""
    df = load_trades()
    if df.empty: return
    
    df['Date'] = df['Timestamp'].dt.date
    daily_groups = df.groupby('Date')
    
    print(f"\n{'='*80}")
    print(f"📅 DAILY BREAKDOWN")
    print(f"{'='*80}")
    print(f"{'Date':<15} {'Trades':<10} {'Win%':<10} {'Total PNL':<15} {'Avg PNL':<15}")
    print(f"{'-'*80}")
    
    for date, group in daily_groups:
        total = len(group)
        wins = len(group[group['PNL_Percent'] > 0])
        win_rate = (wins / total * 100) if total > 0 else 0
        total_pnl = group['PNL_USDT'].sum()
        avg_pnl = group['PNL_USDT'].mean()
        
        print(f"{str(date):<15} {total:<10} {win_rate:<10.2f}% ${total_pnl:<14.2f} ${avg_pnl:<14.2f}")

def analyze_weekly():
    """Analyze weekly performance"""
    df = load_trades()
    if df.empty: return
    
    df['Week'] = df['Timestamp'].dt.isocalendar().week
    df['Year'] = df['Timestamp'].dt.year
    weekly_groups = df.groupby(['Year', 'Week'])
    
    print(f"\n{'='*80}")
    print(f"📆 WEEKLY BREAKDOWN")
    print(f"{'='*80}")
    print(f"{'Week':<15} {'Trades':<10} {'Win%':<10} {'Total PNL':<15} {'Avg PNL':<15}")
    print(f"{'-'*80}")
    
    for (year, week), group in weekly_groups:
        total = len(group)
        wins = len(group[group['PNL_Percent'] > 0])
        win_rate = (wins / total * 100) if total > 0 else 0
        total_pnl = group['PNL_USDT'].sum()
        avg_pnl = group['PNL_USDT'].mean()
        
        print(f"W{week} {year:<10} {total:<10} {win_rate:<10.2f}% ${total_pnl:<14.2f} ${avg_pnl:<14.2f}")

def analyze_by_symbol():
    """Analyze performance by symbol"""
    df = load_trades()
    if df.empty: return
    
    symbol_groups = df.groupby('Symbol')
    
    print(f"\n{'='*100}")
    print(f"🎯 PERFORMANCE BY SYMBOL")
    print(f"{'='*100}")
    print(f"{'Symbol':<15} {'Trades':<10} {'Win%':<10} {'Total PNL':<15} {'Avg PNL':<15} {'Best Trade':<15}")
    print(f"{'-'*100}")
    
    for symbol, group in symbol_groups:
        total = len(group)
        wins = len(group[group['PNL_Percent'] > 0])
        win_rate = (wins / total * 100) if total > 0 else 0
        total_pnl = group['PNL_USDT'].sum()
        avg_pnl = group['PNL_USDT'].mean()
        best_trade = group['PNL_USDT'].max()
        
        print(f"{symbol:<15} {total:<10} {win_rate:<10.2f}% ${total_pnl:<14.2f} ${avg_pnl:<14.2f} ${best_trade:<14.2f}")

def export_to_excel(df):
    """Export trades and analytics to Excel with formatting"""
    try:
        # Try with openpyxl, fallback to xlsxwriter
        try:
            import openpyxl
            engine = 'openpyxl'
        except ImportError:
            try:
                import xlsxwriter
                engine = 'xlsxwriter'
            except ImportError:
                print("⚠️  Installing xlsxwriter...")
                import sys
                import subprocess
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'xlsxwriter', '-q'])
                engine = 'xlsxwriter'
        
        with pd.ExcelWriter(EXCEL_OUTPUT, engine=engine) as writer:
            # Sheet 1: Raw Trades
            df_export = df.copy()
            df_export.to_excel(writer, sheet_name='All Trades', index=False)
            
            # Sheet 2: Daily Summary
            df_copy = df.copy()
            df_copy['Date'] = df_copy['Timestamp'].dt.date
            daily_summary = df_copy.groupby('Date').agg({
                'Symbol': 'count',
                'PNL_USDT': ['sum', 'mean'],
                'PNL_Percent': 'mean'
            }).round(2)
            daily_summary.columns = ['Total Trades', 'Total PNL $', 'Avg PNL $', 'Avg PNL %']
            daily_summary.to_excel(writer, sheet_name='Daily Summary')
            
            # Sheet 3: Weekly Summary
            df_copy['Week'] = df_copy['Timestamp'].dt.isocalendar().week
            df_copy['Year'] = df_copy['Timestamp'].dt.year
            weekly_summary = df_copy.groupby(['Year', 'Week']).agg({
                'Symbol': 'count',
                'PNL_USDT': ['sum', 'mean'],
                'PNL_Percent': 'mean'
            }).round(2)
            weekly_summary.columns = ['Total Trades', 'Total PNL $', 'Avg PNL $', 'Avg PNL %']
            weekly_summary.to_excel(writer, sheet_name='Weekly Summary')
            
            # Sheet 4: Symbol Performance
            symbol_summary = df_copy.groupby('Symbol').agg({
                'Symbol': 'count',
                'PNL_USDT': ['sum', 'mean', 'max', 'min'],
                'PNL_Percent': 'mean'
            }).round(2)
            symbol_summary.columns = ['Total Trades', 'Total PNL $', 'Avg PNL $', 'Best Trade $', 'Worst Trade $', 'Avg PNL %']
            symbol_summary.to_excel(writer, sheet_name='Symbol Performance')
            
            # Sheet 5: Overall Statistics
            overall_stats = calculate_stats(df)
            stats_df = pd.DataFrame(list(overall_stats.items()), columns=['Metric', 'Value'])
            stats_df.to_excel(writer, sheet_name='Overall Stats', index=False)
        
        print(f"✅ Excel file exported: {EXCEL_OUTPUT}")
        return True
    except Exception as e:
        print(f"❌ Excel export failed: {e}")
        return False

def main():
    """Main analytics dashboard"""
    df = load_trades()
    
    if df.empty:
        print("❌ No trades found. Run the bot first!")
        return
    
    # Overall stats
    overall_stats = calculate_stats(df)
    print_stats(overall_stats, "Overall")
    
    # Daily analysis
    analyze_daily()
    
    # Weekly analysis
    analyze_weekly()
    
    # Symbol analysis
    analyze_by_symbol()
    
    # Export to Excel
    print(f"\n{'='*60}")
    print(f"📊 EXPORTING TO EXCEL...")
    export_to_excel(df)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"✅ ANALYSIS COMPLETE")
    print(f"Total records analyzed: {len(df)}")
    print(f"Date range: {df['Timestamp'].min()} to {df['Timestamp'].max()}")
    print(f"📥 Download: {EXCEL_OUTPUT}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
