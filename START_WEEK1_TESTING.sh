#!/bin/bash

# START_WEEK1_TESTING.sh
# Quick setup and start script for Week 1 testing

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          WEEK 1 TESTING — ENHANCED STRATEGY BOT               ║"
echo "║                    December 7-13, 2025                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Check if .env exists
if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo ""
    echo "Please create .env file first:"
    echo "  1. cp .env.example .env"
    echo "  2. Edit .env and add your Binance testnet API keys"
    echo "  3. Run this script again"
    exit 1
fi

# Step 2: Check if API keys are set
if grep -q "your_testnet_api_key_here" .env; then
    echo "❌ ERROR: API keys not configured in .env!"
    echo ""
    echo "Please edit .env and add your Binance testnet API keys:"
    echo "  BINANCE_API_KEY=your_actual_key"
    echo "  BINANCE_API_SECRET=your_actual_secret"
    exit 1
fi

# Step 3: Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Step 4: Install dependencies
echo "✅ Installing dependencies..."
pip install python-dotenv -q

# Step 5: Create logs directory
echo "✅ Creating logs directory..."
mkdir -p week1_logs

# Step 6: Verify imports
echo "✅ Verifying imports..."
python3 -c "from ENHANCED_STRATEGY import enhanced_momentum_strategy; print('   ✓ ENHANCED_STRATEGY imported')" || exit 1
python3 -c "from binance import Client; print('   ✓ python-binance imported')" || exit 1
python3 -c "import pandas as pd; print('   ✓ pandas imported')" || exit 1

# Step 7: Show configuration
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    CONFIGURATION SUMMARY                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Strategy: Enhanced Momentum (7 indicators)"
echo "Min Signal Strength: 60 points"
echo "Daily Loss Limit: -3.0%"
echo "Max Consecutive Losses: 3"
echo "Leverage: 20x"
echo "Order Size: 10 USDT"
echo ""

# Step 8: Ask for confirmation
echo "Ready to start Week 1 testing?"
echo ""
echo "This will:"
echo "  1. Run APEX_TRADER_V3_ENHANCED.py"
echo "  2. Monitor BTCUSDT, ETHUSDT, BNBUSDT"
echo "  3. Log all trades to apex_trades_v3.csv"
echo "  4. Run daily analysis with LOSS_ANALYSIS.py"
echo ""
read -p "Start bot now? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled. Run this script again when ready."
    exit 0
fi

# Step 9: Create daily log file
DATE=$(date +"%Y-%m-%d")
LOG_FILE="week1_logs/${DATE}_session.log"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    STARTING BOT                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Bot starting at: $(date)"
echo "Logs saved to: $LOG_FILE"
echo ""
echo "To stop the bot: Press Ctrl+C"
echo ""
echo "To monitor in another terminal:"
echo "  tail -f $LOG_FILE"
echo ""
echo "To run daily analysis:"
echo "  python3 LOSS_ANALYSIS.py"
echo ""
echo "═════════════════════════════════════════════════════════════════"
echo ""

# Step 10: Start bot with logging
python3 APEX_TRADER_V3_ENHANCED.py 2>&1 | tee -a "$LOG_FILE"

# Step 11: Bot stopped
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    BOT STOPPED                                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Bot stopped at: $(date)"
echo "Session log: $LOG_FILE"
echo ""
echo "To analyze today's trades:"
echo "  python3 LOSS_ANALYSIS.py"
echo ""
echo "To view session log:"
echo "  cat $LOG_FILE"
echo ""
