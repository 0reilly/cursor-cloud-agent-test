# Crypto Trading Agent with HMM Regime Detection

## Overview
This system implements an automated crypto trading agent using Alpaca paper trading. It combines a momentum-based strategy with Hidden Markov Model (HMM) regime detection (inspired by quantitative hedge funds). The agent can run continuously, scan markets, make trading decisions, manage risk, and log performance.

## Key Features
- **HMM Regime Detection**: Detects 5 market regimes (STRONG_BULL, WEAK_BULL, SIDEWAYS, WEAK_BEAR, STRONG_BEAR) using a Gaussian HMM trained on synthetic data.
- **Regime-Aware Strategy**: Adjusts trading signals, position sizes, and confidence based on detected regime.
- **Risk Management**: Includes circuit breaker, position sizing, stop-loss/take-profit, and daily loss limits.
- **Performance Dashboard**: Generates HTML reports with metrics, visualizations, and strategy comparison.
- **Paper Trading Ready**: Uses Alpaca paper trading environment; no real money at risk.

## Installation & Setup
1. Clone repository and install dependencies: `pip install -r requirements.txt`
2. Configure Alpaca API keys in `config.py` (paper trading keys already present).
3. Ensure you have `hmmlearn` installed: `pip install hmmlearn`

## Usage

### Running the Trading Engine
```bash
python3 trading_engine.py --interval 5   # 5-minute scan interval, runs continuously
```

For a single scan (testing):
```bash
python3 trading_engine.py --once
```

Check engine status:
```bash
python3 trading_engine.py --status
```

### Comparing Strategies
```bash
python3 compare_strategies.py
```
Generates a side-by-side comparison of pure algorithmic vs HMM-regime-aware strategies, saving results in `data/`.

### Performance Dashboard
```bash
python3 performance_dashboard.py
```
Generates a performance report HTML and PNG in `reports/`.

## Configuration
Edit `config.py` to adjust:
- Crypto symbols, time frame, lookback period
- Risk parameters (stop loss, max positions, etc.)
- Trading hours (crypto is 24/7)

## Architecture
- `trading_engine.py`: Main orchestration loop
- `strategy.py`: Pure momentum strategy
- `hmm_regime.py`: HMM regime detector and regime-aware strategy wrapper
- `alpaca_client.py`: Alpaca API client
- `risk_manager.py`: Risk management and trade logging
- `compare_strategies.py`: Strategy comparison utility
- `performance_dashboard.py`: Dashboard reporting

## Current Status
- HMM regime-aware strategy is integrated as the default strategy.
- The system is ready for continuous operation in paper trading.
- **Note**: A stuck MKRUSD position is triggering the circuit breaker; close this position manually via Alpaca web interface to resume trading.

## Performance Metrics
- Trade logs: `data/trades.csv`
- Risk metrics: `data/risk_metrics.json`
- Strategy comparison results: `data/strategy_comparison_results_*.json`
- Dashboard reports: `reports/`

## Next Steps
1. Close the MKRUSD position to deactivate circuit breaker.
2. Monitor the agent's performance over several days.
3. Fine-tune HMM parameters or feature extraction based on live results.
4. Extend dashboard with regime history visualization.

## Disclaimer
This is a research project for educational purposes. Use at your own risk. Past performance is not indicative of future results.