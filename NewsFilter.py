# NewsFilter.py — HIGH IMPACT NEWS BLOCKER
# Prevents trading during major economic events and crypto news bombs

import requests
import time
import json
import os
from datetime import datetime

# Crypto news sources to monitor
WATCHED_ACCOUNTS = ["WatcherGuru", "CryptoPanicCom", "tier10k", "TheBlockbeats"]

# High-impact keywords that should pause trading
BAD_KEYWORDS = [
    'fomc', 'fed', 'cpi', 'ppi', 'sec', 'liquidation', 'etf decision', 
    'binance', 'hack', 'exploit', 'breach', 'bankruptcy', 'collapse',
    'emergency', 'crisis', 'crash', 'circuit breaker', 'halt', 'suspend'
]

# Cache file to avoid excessive API calls
NEWS_CACHE_FILE = 'news_cache.json'
CACHE_DURATION = 300  # 5 minutes

def load_news_cache():
    """Load cached news data"""
    try:
        if os.path.exists(NEWS_CACHE_FILE):
            with open(NEWS_CACHE_FILE, 'r') as f:
                data = json.load(f)
                # Check if cache is still valid
                if time.time() - data.get('timestamp', 0) < CACHE_DURATION:
                    return data.get('news', [])
    except:
        pass
    return []

def save_news_cache(news_data):
    """Save news data to cache"""
    try:
        with open(NEWS_CACHE_FILE, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'news': news_data
            }, f)
    except:
        pass

def fetch_cryptopanic_news():
    """
    Fetch hot news from CryptoPanic API
    Note: Replace 'YOUR_TOKEN' with actual API token from https://cryptopanic.com/developers/
    """
    try:
        # Using free tier (no auth token required for basic access)
        url = "https://cryptopanic.com/api/v1/posts/?public=true&kind=news&filter=hot"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
    except Exception as e:
        print(f"[NEWS] CryptoPanic fetch error: {e}")
    
    return []

def fetch_coingecko_events():
    """
    Fetch major events from CoinGecko API (free, no auth required)
    """
    try:
        url = "https://api.coingecko.com/api/v3/events?language=en"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', [])
    except Exception as e:
        print(f"[NEWS] CoinGecko fetch error: {e}")
    
    return []

def is_high_impact_news():
    """
    Check if there's high-impact news that should pause trading
    Returns: (should_pause: bool, reason: str)
    """
    try:
        # Try cache first
        cached_news = load_news_cache()
        if cached_news:
            news_data = cached_news
        else:
            # Fetch fresh news
            news_data = fetch_cryptopanic_news()
            if not news_data:
                news_data = fetch_coingecko_events()
            
            # Cache the results
            if news_data:
                save_news_cache(news_data)
        
        if not news_data:
            return False, "No news data available"
        
        # Check recent news (last 30 minutes)
        current_time = time.time()
        recent_news = []
        
        for item in news_data:
            # Handle different API response formats
            if isinstance(item, dict):
                # CryptoPanic format
                if 'published_at' in item:
                    pub_time = item['published_at']
                    if isinstance(pub_time, str):
                        try:
                            pub_timestamp = datetime.fromisoformat(pub_time.replace('Z', '+00:00')).timestamp()
                        except:
                            pub_timestamp = 0
                    else:
                        pub_timestamp = pub_time
                    
                    if current_time - pub_timestamp < 1800:  # 30 minutes
                        recent_news.append(item)
                
                # CoinGecko format
                elif 'start_date' in item:
                    recent_news.append(item)
        
        if not recent_news:
            return False, "Clear"
        
        # Analyze recent news for bad keywords
        titles_and_descriptions = []
        for item in recent_news:
            title = item.get('title', '') or item.get('name', '')
            description = item.get('description', '') or item.get('description', '')
            source = item.get('source', {}).get('title', 'Unknown') if isinstance(item.get('source'), dict) else 'Unknown'
            
            titles_and_descriptions.append(f"{title} {description}".lower())
            
            # Check for bad keywords
            for keyword in BAD_KEYWORDS:
                if keyword in title.lower() or keyword in description.lower():
                    return True, f"🚨 HIGH IMPACT NEWS DETECTED: {title[:60]}... (Source: {source})"
        
        # Check combined text for multiple bad keywords
        combined_text = " | ".join(titles_and_descriptions)
        bad_keyword_count = sum(1 for kw in BAD_KEYWORDS if kw in combined_text)
        
        if bad_keyword_count >= 2:
            return True, f"⚠️ MULTIPLE HIGH-IMPACT NEWS EVENTS DETECTED — TRADING PAUSED"
        
        return False, "Clear"
    
    except Exception as e:
        print(f"[NEWS FILTER ERROR] {e}")
        return False, "Error checking news"

def should_pause_trading():
    """
    Main function to determine if trading should be paused
    Returns: (should_pause: bool, reason: str)
    """
    is_paused, reason = is_high_impact_news()
    
    if is_paused:
        print(f"[⚠️ NEWS FILTER] {reason}")
        return True, reason
    
    return False, reason

# Test function
if __name__ == "__main__":
    print("Testing NewsFilter...")
    should_pause, reason = should_pause_trading()
    print(f"Trading paused: {should_pause}")
    print(f"Reason: {reason}")
