#!/bin/bash

echo "🔍 VERIFYING ANTI-DEGEN SYSTEM INSTALLATION"
echo "=============================================="
echo ""

# Check Python files
echo "📝 Checking Python files..."
files=(
    "NewsFilter.py"
    "DailyLimits.py"
    "ProfitManager.py"
    "MAIN_LOOP_TEMPLATE.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file (MISSING)"
    fi
done

echo ""
echo "📚 Checking documentation files..."
docs=(
    "INTEGRATION_GUIDE.md"
    "ANTI_DEGEN_RULES.md"
    "IMPLEMENTATION_COMPLETE.md"
    "QUICK_START.md"
)

for doc in "${docs[@]}"; do
    if [ -f "$doc" ]; then
        echo "✅ $doc"
    else
        echo "❌ $doc (MISSING)"
    fi
done

echo ""
echo "🐍 Checking Python imports..."
python3 -c "from NewsFilter import should_pause_trading; print('✅ NewsFilter imports OK')" 2>/dev/null || echo "❌ NewsFilter import failed"
python3 -c "from DailyLimits import DailyLimitsManager; print('✅ DailyLimits imports OK')" 2>/dev/null || echo "❌ DailyLimits import failed"
python3 -c "from ProfitManager import manage_open_positions; print('✅ ProfitManager imports OK')" 2>/dev/null || echo "❌ ProfitManager import failed"

echo ""
echo "✅ INSTALLATION VERIFICATION COMPLETE"
echo "=============================================="
