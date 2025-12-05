# DailyLimits.py — DAILY PNL TRACKING & LIMITS
# Prevents over-trading and enforces daily profit/loss limits

import json
import os
import time
from datetime import datetime, timedelta
from binance import Client

# Configuration
MAX_TRADES_PER_DAY = 10
DAILY_PNL_TARGET = 8.0  # 8% real PnL → stop trading for the day
DAILY_LOSS_LIMIT = -3.0  # Hit -3% → bot sleeps 24h

# Data file for tracking
DAILY_LIMITS_FILE = 'daily_limits.json'

class DailyLimitsManager:
    def __init__(self, api_key, api_secret, testnet=True):
        self.client = Client(api_key=api_key, api_secret=api_secret, testnet=testnet)
        self.daily_data = self.load_daily_data()
    
    def load_daily_data(self):
        """Load daily tracking data from file"""
        try:
            if os.path.exists(DAILY_LIMITS_FILE):
                with open(DAILY_LIMITS_FILE, 'r') as f:
                    data = json.load(f)
                    # Reset if it's a new day
                    if self.is_new_day(data.get('date', '')):
                        return self.create_new_daily_record()
                    return data
        except:
            pass
        
        return self.create_new_daily_record()
    
    def create_new_daily_record(self):
        """Create a fresh daily record"""
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'trades_count': 0,
            'daily_pnl': 0.0,
            'daily_pnl_percent': 0.0,
            'trades': [],
            'is_paused': False,
            'pause_reason': '',
            'pause_until': None
        }
    
    def is_new_day(self, date_str):
        """Check if we're in a new day"""
        try:
            stored_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = datetime.now().date()
            return stored_date < today
        except:
            return True
    
    def save_daily_data(self):
        """Save daily tracking data to file"""
        try:
            with open(DAILY_LIMITS_FILE, 'w') as f:
                json.dump(self.daily_data, f, indent=2)
        except Exception as e:
            print(f"[DAILY LIMITS] Error saving data: {e}")
    
    def get_account_balance(self):
        """Get current account balance in USDT"""
        try:
            account = self.client.futures_account()
            total_balance = float(account['totalWalletBalance'])
            return total_balance
        except Exception as e:
            print(f"[DAILY LIMITS] Error fetching balance: {e}")
            return 0.0
    
    def get_daily_pnl(self):
        """Calculate daily PnL from all closed trades"""
        try:
            # Get all trades from today
            trades = self.client.futures_account_trades()
            
            today = datetime.now().date()
            daily_pnl = 0.0
            
            for trade in trades:
                trade_time = datetime.fromtimestamp(trade['time'] / 1000).date()
                if trade_time == today:
                    # realizedPnl is already in USDT
                    daily_pnl += float(trade.get('realizedPnl', 0))
            
            return daily_pnl
        except Exception as e:
            print(f"[DAILY LIMITS] Error calculating PnL: {e}")
            return 0.0
    
    def get_daily_pnl_percent(self):
        """Calculate daily PnL as percentage of account"""
        try:
            account_balance = self.get_account_balance()
            if account_balance <= 0:
                return 0.0
            
            daily_pnl = self.get_daily_pnl()
            pnl_percent = (daily_pnl / account_balance) * 100
            
            return pnl_percent
        except Exception as e:
            print(f"[DAILY LIMITS] Error calculating PnL %: {e}")
            return 0.0
    
    def check_daily_limits(self):
        """
        Check if daily limits have been exceeded
        Returns: (should_pause: bool, reason: str)
        """
        # Check if pause is still active
        if self.daily_data['is_paused']:
            pause_until = self.daily_data.get('pause_until')
            if pause_until and time.time() < pause_until:
                return True, f"⏸️ TRADING PAUSED: {self.daily_data['pause_reason']}"
            else:
                # Pause duration expired, reset
                self.daily_data['is_paused'] = False
                self.daily_data['pause_reason'] = ''
                self.daily_data['pause_until'] = None
                self.save_daily_data()
        
        # Update current PnL
        daily_pnl = self.get_daily_pnl()
        daily_pnl_percent = self.get_daily_pnl_percent()
        
        self.daily_data['daily_pnl'] = daily_pnl
        self.daily_data['daily_pnl_percent'] = daily_pnl_percent
        
        # Check profit target
        if daily_pnl_percent >= DAILY_PNL_TARGET:
            self.daily_data['is_paused'] = True
            self.daily_data['pause_reason'] = f"🎯 DAILY PROFIT TARGET HIT: +{daily_pnl_percent:.2f}%"
            self.daily_data['pause_until'] = None  # No time limit, manual reset needed
            self.save_daily_data()
            return True, self.daily_data['pause_reason']
        
        # Check loss limit
        if daily_pnl_percent <= DAILY_LOSS_LIMIT:
            pause_until = time.time() + (24 * 3600)  # 24 hour pause
            self.daily_data['is_paused'] = True
            self.daily_data['pause_reason'] = f"🛑 DAILY LOSS LIMIT HIT: {daily_pnl_percent:.2f}% (24h pause)"
            self.daily_data['pause_until'] = pause_until
            self.save_daily_data()
            return True, self.daily_data['pause_reason']
        
        # Check trade count
        if self.daily_data['trades_count'] >= MAX_TRADES_PER_DAY:
            self.daily_data['is_paused'] = True
            self.daily_data['pause_reason'] = f"📊 MAX TRADES PER DAY REACHED: {MAX_TRADES_PER_DAY}"
            self.daily_data['pause_until'] = None
            self.save_daily_data()
            return True, self.daily_data['pause_reason']
        
        self.save_daily_data()
        return False, f"✅ Daily limits OK | Trades: {self.daily_data['trades_count']}/{MAX_TRADES_PER_DAY} | PnL: {daily_pnl_percent:+.2f}%"
    
    def log_trade(self, symbol, direction, pnl_usdt, pnl_percent):
        """Log a completed trade"""
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'direction': direction,
            'pnl_usdt': pnl_usdt,
            'pnl_percent': pnl_percent
        }
        
        self.daily_data['trades'].append(trade_record)
        self.daily_data['trades_count'] += 1
        self.save_daily_data()
    
    def reset_daily_limits(self):
        """Manually reset daily limits (for manual override)"""
        self.daily_data = self.create_new_daily_record()
        self.save_daily_data()
        print("[DAILY LIMITS] Daily limits reset")
    
    def get_status(self):
        """Get current daily limits status"""
        daily_pnl_percent = self.get_daily_pnl_percent()
        
        status = {
            'date': self.daily_data['date'],
            'trades_count': self.daily_data['trades_count'],
            'max_trades': MAX_TRADES_PER_DAY,
            'daily_pnl_percent': daily_pnl_percent,
            'daily_pnl_target': DAILY_PNL_TARGET,
            'daily_loss_limit': DAILY_LOSS_LIMIT,
            'is_paused': self.daily_data['is_paused'],
            'pause_reason': self.daily_data['pause_reason'],
            'trades': self.daily_data['trades']
        }
        
        return status

# Test function
if __name__ == "__main__":
    from LiveTradingConfig import API_KEY, API_SECRET, testnet
    
    manager = DailyLimitsManager(API_KEY, API_SECRET, testnet)
    
    print("Daily Limits Status:")
    status = manager.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    should_pause, reason = manager.check_daily_limits()
    print(f"\nShould pause trading: {should_pause}")
    print(f"Reason: {reason}")
