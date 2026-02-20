"""
Integration Test for Crypto Trading System
Tests all components with real Alpaca paper trading API
"""

import sys
import time
import json
from datetime import datetime
import pandas as pd

def test_all_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    modules = [
        'alpaca_trade_api',
        'pandas', 
        'numpy',
        'ta',
        'schedule',
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            return False
    
    # Test our own modules
    our_modules = [
        'config',
        'alpaca_client',
        'strategy', 
        'risk_manager',
        'trading_engine',
    ]
    
    for module in our_modules:
        try:
            __import__(module)
            print(f"  ✅ {module} (local)")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            return False
    
    print("✅ All imports successful\n")
    return True


def test_alpaca_connection():
    """Test Alpaca API connection"""
    print("Testing Alpaca connection...")
    
    try:
        from alpaca_client import AlpacaClient
        
        client = AlpacaClient()
        account = client.get_account()
        
        if account:
            print(f"  ✅ Connection successful")
            print(f"     Account: {account['account_number']}")
            print(f"     Cash: ${account['cash']:,.2f}")
            print(f"     Portfolio Value: ${account['portfolio_value']:,.2f}")
            
            # Test market data
            btc_data = client.get_market_data("BTC/USD", timeframe="5Min", limit=10)
            if not btc_data.empty:
                print(f"  ✅ Market data: {len(btc_data)} BTC bars retrieved")
                print(f"     Latest price: ${btc_data.iloc[-1]['close']:.2f}")
            else:
                print(f"  ⚠️  No BTC data returned (might be outside trading hours)")
            
            # Test positions
            positions = client.get_positions()
            print(f"  ✅ Positions: {len(positions)} current positions")
            
            return True
        else:
            print(f"  ❌ Failed to get account")
            return False
            
    except Exception as e:
        print(f"  ❌ Connection test failed: {e}")
        return False


def test_strategy():
    """Test strategy with real market data"""
    print("\nTesting strategy with real data...")
    
    try:
        from alpaca_client import AlpacaClient
        from strategy import CryptoMomentumStrategy
        
        client = AlpacaClient()
        strategy = CryptoMomentumStrategy()
        
        # Get real market data
        df = client.get_market_data("BTC/USD", timeframe="5Min", limit=100)
        
        if df.empty or len(df) < 20:
            print(f"  ⚠️  Insufficient data for strategy test")
            return False
        
        # Test indicators
        df_with_indicators = strategy.calculate_indicators(df)
        indicator_count = len([col for col in df_with_indicators.columns 
                              if 'sma' in col or 'rsi' in col or 'macd' in col])
        print(f"  ✅ Indicators calculated: {indicator_count} technical indicators")
        
        # Test signal generation
        signal = strategy.generate_signals(df_with_indicators)
        print(f"  ✅ Signal generated: {signal['signal']} (confidence: {signal['confidence']:.2f})")
        if signal['reasons']:
            print(f"     Reasons: {', '.join(signal['reasons'][:2])}...")
        
        # Test complete analysis
        analysis = strategy.analyze_market(df, account_cash=10000)
        print(f"  ✅ Complete analysis: {analysis.get('signal', 'error')}")
        
        # Test position sizing
        if analysis.get('signal') != 'hold':
            print(f"  ✅ Position size ready for trading")
        else:
            print(f"  ✅ Hold signal (no position sizing needed)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Strategy test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_risk_manager():
    """Test risk management module"""
    print("\nTesting risk manager...")
    
    try:
        from risk_manager import RiskManager
        
        risk_mgr = RiskManager(data_dir="data")
        
        # Test position sizing
        quantity, metrics = risk_mgr.calculate_position_size(
            account_cash=10000,
            current_price=50000,
            confidence=0.7,
            volatility=0.02,
            existing_positions=[]
        )
        
        print(f"  ✅ Position size calculated: {quantity:.6f}")
        print(f"     Value: ${metrics['position_value']:.2f}")
        print(f"     Stop loss: ${metrics['stop_loss']:.2f}")
        
        # Test trade validation
        mock_positions = [
            {'symbol': 'ETH/USD', 'qty': 1.0, 'market_value': 3000, 'side': 'buy'},
        ]
        
        is_valid, reason = risk_mgr.validate_trade(
            symbol='BTC/USD',
            qty=0.01,
            price=50000,
            side='buy',
            positions=mock_positions,
            account_cash=10000
        )
        
        print(f"  ✅ Trade validation: {'Valid' if is_valid else 'Invalid'} - {reason}")
        
        # Test performance summary
        performance = risk_mgr.get_performance_summary()
        print(f"  ✅ Performance tracking: {performance['total_trades']} trades logged")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Risk manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trading_engine_single_scan():
    """Test trading engine with a single market scan"""
    print("\nTesting trading engine (single scan)...")
    
    try:
        from trading_engine import TradingEngine
        
        engine = TradingEngine(scan_interval_minutes=5)
        
        # Get initial status
        status = engine.get_status()
        print(f"  ✅ Engine initialized")
        print(f"     Account: {status['account']['account_number']}")
        print(f"     Cash: ${status['account']['cash']:,.2f}")
        
        # Run single scan
        print("  Running market scan...")
        engine.run_once()
        
        # Get updated status
        updated_status = engine.get_status()
        print(f"  ✅ Scan completed")
        print(f"     Total scans: {updated_status['engine']['total_scans']}")
        print(f"     Active positions: {updated_status['engine']['active_positions']}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Trading engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_pipeline():
    """Test the complete trading pipeline"""
    print("\n" + "="*60)
    print("COMPLETE PIPELINE TEST")
    print("="*60)
    
    all_passed = True
    
    # Test 1: Imports
    if not test_all_imports():
        all_passed = False
        print("❌ Import test failed, aborting further tests")
        return False
    
    # Test 2: Alpaca connection
    if not test_alpaca_connection():
        all_passed = False
        print("❌ Alpaca connection failed, aborting further tests")
        return False
    
    # Test 3: Strategy
    if not test_strategy():
        all_passed = False
        print("⚠️  Strategy test issues, continuing...")
    
    # Test 4: Risk manager
    if not test_risk_manager():
        all_passed = False
        print("⚠️  Risk manager test issues, continuing...")
    
    # Test 5: Trading engine
    if not test_trading_engine_single_scan():
        all_passed = False
        print("⚠️  Trading engine test issues")
    
    # Final summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if all_passed:
        print("✅ ALL TESTS PASSED - System is ready for paper trading!")
        print("\nTo start automated trading:")
        print("  python trading_engine.py")
        print("\nTo run a single scan:")
        print("  python trading_engine.py --once")
        print("\nTo check status:")
        print("  python trading_engine.py --status")
    else:
        print("⚠️  Some tests had issues, review above output")
    
    return all_passed


def check_account_health():
    """Check account health and trading readiness"""
    print("\n" + "="*60)
    print("ACCOUNT HEALTH CHECK")
    print("="*60)
    
    try:
        from alpaca_client import AlpacaClient
        
        client = AlpacaClient()
        account = client.get_account()
        
        if not account:
            print("❌ Cannot access account")
            return
        
        print(f"Account: {account['account_number']} ({account['status']})")
        print(f"Cash: ${account['cash']:,.2f}")
        print(f"Buying Power: ${account['buying_power']:,.2f}")
        print(f"Portfolio Value: ${account['portfolio_value']:,.2f}")
        print(f"Equity: ${account['equity']:,.2f}")
        
        # Check for issues
        issues = []
        
        if account['trading_blocked']:
            issues.append("Trading is blocked")
        
        if account['account_blocked']:
            issues.append("Account is blocked")
        
        if account['daytrade_count'] >= 3:
            issues.append(f"Day trade limit reached: {account['daytrade_count']}/3")
        
        if account['cash'] < 100:
            issues.append(f"Low cash: ${account['cash']:.2f}")
        
        # Check positions
        positions = client.get_positions()
        print(f"\nPositions: {len(positions)}")
        
        for pos in positions:
            print(f"  {pos['symbol']}: {pos['qty']} @ ${pos['avg_entry_price']:.2f} "
                  f"(PnL: ${pos['unrealized_pl']:.2f}, {pos['unrealized_plpc']:.1%})")
            
            # Check for stuck positions
            if 'asset not active' in str(pos).lower():
                issues.append(f"Stuck position: {pos['symbol']}")
        
        # Summary
        if issues:
            print(f"\n⚠️  ISSUES FOUND:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print(f"\n✅ Account is healthy and ready for trading")
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")


if __name__ == "__main__":
    print("CRYPTO TRADING SYSTEM - INTEGRATION TEST")
    print("="*60)
    
    # Run health check first
    check_account_health()
    
    # Run full pipeline test
    success = test_full_pipeline()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)