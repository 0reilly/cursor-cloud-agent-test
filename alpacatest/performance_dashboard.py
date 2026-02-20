#!/usr/bin/env python3
"""
Performance Dashboard for Crypto Trading System
Generates visualizations and reports on trading performance
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import json
import os
import sys
from typing import Dict, List, Any, Optional
import warnings
warnings.filterwarnings('ignore')

# Set plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


class PerformanceDashboard:
    """Dashboard for visualizing trading performance"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.trade_log_file = os.path.join(data_dir, "trades.csv")
        self.risk_metrics_file = os.path.join(data_dir, "risk_metrics.json")
        self.comparison_files = []  # Will be populated with comparison results
        
        print("Performance Dashboard Initialized")
        print("=" * 60)
        
        # Check for data files
        self._check_data_files()
    
    def _check_data_files(self):
        """Check for existence of data files"""
        print("Checking data files...")
        
        files = {
            "Trade Log": self.trade_log_file,
            "Risk Metrics": self.risk_metrics_file,
        }
        
        for name, path in files.items():
            if os.path.exists(path):
                print(f"  ✓ {name}: {path}")
            else:
                print(f"  ✗ {name}: Not found")
        
        # Look for comparison files
        comparison_files = []
        if os.path.exists(self.data_dir):
            for f in os.listdir(self.data_dir):
                if f.startswith("strategy_comparison_") and f.endswith(".json"):
                    comparison_files.append(os.path.join(self.data_dir, f))
        
        self.comparison_files = sorted(comparison_files, reverse=True)  # Newest first
        print(f"  ✓ Comparison files: {len(self.comparison_files)} found")
        
        # Look for plot files
        plot_files = []
        if os.path.exists(self.data_dir):
            for f in os.listdir(self.data_dir):
                if f.startswith("comparison_plot_") and f.endswith(".png"):
                    plot_files.append(os.path.join(self.data_dir, f))
        
        print(f"  ✓ Plot files: {len(plot_files)} found")
    
    def load_trade_data(self) -> Optional[pd.DataFrame]:
        """Load trade log data"""
        if not os.path.exists(self.trade_log_file):
            print(f"Trade log file not found: {self.trade_log_file}")
            return None
        
        try:
            trades_df = pd.read_csv(self.trade_log_file)
            print(f"Loaded {len(trades_df)} trades from log")
            
            # Convert timestamp if present
            if 'timestamp' in trades_df.columns:
                trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
                trades_df = trades_df.sort_values('timestamp')
            
            return trades_df
        except Exception as e:
            print(f"Error loading trade data: {e}")
            return None
    
    def load_risk_metrics(self) -> Dict[str, Any]:
        """Load risk metrics"""
        if not os.path.exists(self.risk_metrics_file):
            print(f"Risk metrics file not found: {self.risk_metrics_file}")
            return {}
        
        try:
            with open(self.risk_metrics_file, 'r') as f:
                metrics = json.load(f)
            print(f"Loaded risk metrics")
            return metrics
        except Exception as e:
            print(f"Error loading risk metrics: {e}")
            return {}
    
    def load_latest_comparison(self) -> Optional[Dict[str, Any]]:
        """Load latest comparison results"""
        if not self.comparison_files:
            print("No comparison files found")
            return None
        
        latest_file = self.comparison_files[0]  # Newest
        try:
            with open(latest_file, 'r') as f:
                comparison_data = json.load(f)
            print(f"Loaded comparison data from {os.path.basename(latest_file)}")
            return comparison_data
        except Exception as e:
            print(f"Error loading comparison data: {e}")
            return None
    
    def generate_performance_report(self, output_dir: str = "reports"):
        """Generate comprehensive performance report"""
        print(f"\n{'='*60}")
        print("GENERATING PERFORMANCE REPORT")
        print(f"{'='*60}")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_prefix = f"performance_report_{timestamp}"
        
        # Load data
        trades_df = self.load_trade_data()
        risk_metrics = self.load_risk_metrics()
        comparison_data = self.load_latest_comparison()
        
        # Generate visualizations
        fig_files = []
        
        if trades_df is not None and len(trades_df) > 0:
            fig1 = self._plot_trade_performance(trades_df, output_dir, report_prefix)
            fig_files.append(fig1)
            
            fig2 = self._plot_pnl_over_time(trades_df, output_dir, report_prefix)
            fig_files.append(fig2)
        
        if comparison_data:
            fig3 = self._plot_strategy_comparison(comparison_data, output_dir, report_prefix)
            fig_files.append(fig3)
        
        # Generate HTML report
        html_file = self._generate_html_report(
            trades_df, risk_metrics, comparison_data, 
            fig_files, output_dir, report_prefix
        )
        
        print(f"\n{'='*60}")
        print("REPORT GENERATION COMPLETE")
        print(f"{'='*60}")
        print(f"HTML Report: {html_file}")
        for fig in fig_files:
            print(f"Chart: {fig}")
        
        return html_file
    
    def _plot_trade_performance(self, trades_df: pd.DataFrame, 
                               output_dir: str, prefix: str) -> str:
        """Plot trade performance metrics"""
        print("  Generating trade performance charts...")
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Trade Performance Analysis', fontsize=16)
        
        # 1. Trade outcomes (win/loss)
        if 'realized_pnl' in trades_df.columns:
            wins = (trades_df['realized_pnl'] > 0).sum()
            losses = (trades_df['realized_pnl'] < 0).sum()
            neutrals = (trades_df['realized_pnl'] == 0).sum()
            
            labels = ['Wins', 'Losses', 'Neutral']
            sizes = [wins, losses, neutrals]
            colors = ['#2ecc71', '#e74c3c', '#95a5a6']
            
            axes[0, 0].pie([s for s in sizes if s > 0], 
                          labels=[l for l, s in zip(labels, sizes) if s > 0],
                          autopct='%1.1f%%', colors=colors, startangle=90)
            axes[0, 0].set_title('Trade Outcomes')
        
        # 2. PnL distribution
        if 'realized_pnl' in trades_df.columns and 'realized_pnl_pct' in trades_df.columns:
            # Histogram of PnL percentages
            axes[0, 1].hist(trades_df['realized_pnl_pct'].dropna(), bins=20, 
                           alpha=0.7, edgecolor='black')
            axes[0, 1].axvline(x=0, color='red', linestyle='--', alpha=0.5)
            axes[0, 1].set_xlabel('PnL (%)')
            axes[0, 1].set_ylabel('Frequency')
            axes[0, 1].set_title('PnL Distribution')
            axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Cumulative PnL over time
        if 'timestamp' in trades_df.columns and 'realized_pnl' in trades_df.columns:
            trades_df = trades_df.sort_values('timestamp')
            trades_df['cumulative_pnl'] = trades_df['realized_pnl'].cumsum()
            
            axes[1, 0].plot(trades_df['timestamp'], trades_df['cumulative_pnl'], 
                          marker='o', markersize=3, linewidth=2)
            axes[1, 0].set_xlabel('Date')
            axes[1, 0].set_ylabel('Cumulative PnL ($)')
            axes[1, 0].set_title('Cumulative Profit & Loss')
            axes[1, 0].grid(True, alpha=0.3)
            plt.setp(axes[1, 0].xaxis.get_majorticklabels(), rotation=45)
        
        # 4. Trade frequency by symbol
        if 'symbol' in trades_df.columns:
            symbol_counts = trades_df['symbol'].value_counts()
            axes[1, 1].bar(range(len(symbol_counts)), symbol_counts.values)
            axes[1, 1].set_xlabel('Symbol')
            axes[1, 1].set_ylabel('Number of Trades')
            axes[1, 1].set_title('Trade Frequency by Symbol')
            axes[1, 1].set_xticks(range(len(symbol_counts)))
            axes[1, 1].set_xticklabels(symbol_counts.index, rotation=45, ha='right')
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save figure
        filename = f"{prefix}_trade_performance.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def _plot_pnl_over_time(self, trades_df: pd.DataFrame,
                           output_dir: str, prefix: str) -> str:
        """Plot PnL over time with additional metrics"""
        print("  Generating PnL over time chart...")
        
        if 'timestamp' not in trades_df.columns or 'realized_pnl' not in trades_df.columns:
            return ""
        
        trades_df = trades_df.sort_values('timestamp')
        trades_df['cumulative_pnl'] = trades_df['realized_pnl'].cumsum()
        
        # Calculate rolling metrics
        trades_df['rolling_20_pnl'] = trades_df['realized_pnl'].rolling(window=min(20, len(trades_df))).mean()
        
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        # Plot 1: Cumulative PnL
        axes[0].plot(trades_df['timestamp'], trades_df['cumulative_pnl'], 
                    linewidth=2, color='#3498db', label='Cumulative PnL')
        axes[0].fill_between(trades_df['timestamp'], 0, trades_df['cumulative_pnl'],
                            alpha=0.3, color='#3498db')
        axes[0].set_ylabel('Cumulative PnL ($)')
        axes[0].set_title('Cumulative Profit & Loss Over Time')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Plot 2: Daily PnL (if we have enough data)
        if len(trades_df) > 1:
            # Group by day if possible
            trades_df['date'] = trades_df['timestamp'].dt.date
            daily_pnl = trades_df.groupby('date')['realized_pnl'].sum()
            
            if len(daily_pnl) > 1:
                axes[1].bar(range(len(daily_pnl)), daily_pnl.values,
                           color=['#2ecc71' if x > 0 else '#e74c3c' for x in daily_pnl.values])
                axes[1].set_xlabel('Trading Day')
                axes[1].set_ylabel('Daily PnL ($)')
                axes[1].set_title('Daily Profit & Loss')
                axes[1].set_xticks(range(len(daily_pnl)))
                axes[1].set_xticklabels([str(d) for d in daily_pnl.index], rotation=45, ha='right')
                axes[1].axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        plt.tight_layout()
        
        # Save figure
        filename = f"{prefix}_pnl_over_time.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def _plot_strategy_comparison(self, comparison_data: Dict[str, Any],
                                 output_dir: str, prefix: str) -> str:
        """Plot strategy comparison results"""
        print("  Generating strategy comparison chart...")
        
        if 'comparisons' not in comparison_data or not comparison_data['comparisons']:
            return ""
        
        comparisons = comparison_data['comparisons']
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Extract data
        symbols = [c['symbol'] for c in comparisons]
        pure_conf = [c['pure_algorithmic']['confidence'] for c in comparisons]
        hmm_conf = [c['hmm_regime_aware']['confidence'] for c in comparisons]
        
        # Plot 1: Confidence comparison
        x = np.arange(len(symbols))
        width = 0.35
        
        axes[0].bar(x - width/2, pure_conf, width, label='Pure Algorithmic', alpha=0.8)
        axes[0].bar(x + width/2, hmm_conf, width, label='HMM-Regime-Aware', alpha=0.8)
        axes[0].set_xlabel('Symbol')
        axes[0].set_ylabel('Confidence')
        axes[0].set_title('Strategy Confidence Comparison')
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(symbols, rotation=45, ha='right')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Plot 2: Signal distribution
        pure_signals = {'buy': 0, 'sell': 0, 'hold': 0}
        hmm_signals = {'buy': 0, 'sell': 0, 'hold': 0}
        
        for comp in comparisons:
            pure_signal = comp['pure_algorithmic']['signal']
            hmm_signal = comp['hmm_regime_aware']['signal']
            pure_signals[pure_signal] += 1
            hmm_signals[hmm_signal] += 1
        
        x_labels = ['Buy', 'Sell', 'Hold']
        pure_counts = [pure_signals['buy'], pure_signals['sell'], pure_signals['hold']]
        hmm_counts = [hmm_signals['buy'], hmm_signals['sell'], hmm_signals['hold']]
        
        x_pos = np.arange(len(x_labels))
        axes[1].bar(x_pos - 0.2, pure_counts, 0.4, label='Pure', alpha=0.8)
        axes[1].bar(x_pos + 0.2, hmm_counts, 0.4, label='HMM', alpha=0.8)
        axes[1].set_xlabel('Signal')
        axes[1].set_ylabel('Count')
        axes[1].set_title('Signal Distribution')
        axes[1].set_xticks(x_pos)
        axes[1].set_xticklabels(x_labels)
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save figure
        filename = f"{prefix}_strategy_comparison.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def _generate_html_report(self, trades_df: Optional[pd.DataFrame],
                             risk_metrics: Dict[str, Any],
                             comparison_data: Optional[Dict[str, Any]],
                             fig_files: List[str],
                             output_dir: str, prefix: str) -> str:
        """Generate HTML report"""
        print("  Generating HTML report...")
        
        html_file = os.path.join(output_dir, f"{prefix}.html")
        
        # Calculate summary statistics
        summary_stats = self._calculate_summary_stats(trades_df, risk_metrics, comparison_data)
        
        # Generate HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Trading Performance Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 20px 0; }}
        .metric {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #3498db; }}
        .metric h3 {{ margin-top: 0; color: #2c3e50; font-size: 14px; text-transform: uppercase; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .metric-positive {{ color: #27ae60; }}
        .metric-negative {{ color: #e74c3c; }}
        .chart {{ margin: 20px 0; text-align: center; }}
        .chart img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 5px; }}
        .timestamp {{ color: #7f8c8d; font-size: 12px; text-align: right; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Crypto Trading Performance Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Performance Summary</h2>
        <div class="summary">
            <div class="metric">
                <h3>Total Trades</h3>
                <div class="metric-value">{summary_stats.get('total_trades', 0)}</div>
            </div>
            <div class="metric">
                <h3>Win Rate</h3>
                <div class="metric-value {'' if summary_stats.get('win_rate', 0) >= 0.5 else 'metric-negative'}">
                    {summary_stats.get('win_rate_formatted', '0.0%')}
                </div>
            </div>
            <div class="metric">
                <h3>Total PnL</h3>
                <div class="metric-value {summary_stats.get('pnl_class', '')}">
                    ${summary_stats.get('total_pnl_formatted', '0.00')}
                </div>
            </div>
            <div class="metric">
                <h3>Avg Trade PnL</h3>
                <div class="metric-value {summary_stats.get('avg_pnl_class', '')}">
                    ${summary_stats.get('avg_trade_pnl_formatted', '0.00')}
                </div>
            </div>
            <div class="metric">
                <h3>Sharpe Ratio</h3>
                <div class="metric-value">
                    {summary_stats.get('sharpe_ratio_formatted', '0.00')}
                </div>
            </div>
            <div class="metric">
                <h3>Max Drawdown</h3>
                <div class="metric-value metric-negative">
                    {summary_stats.get('max_drawdown_formatted', '0.0%')}
                </div>
            </div>
        </div>
        
        <h2>Visualizations</h2>
"""
        
        # Add charts
        for fig_file in fig_files:
            fig_name = os.path.basename(fig_file)
            html_content += f"""
        <div class="chart">
            <h3>{fig_name.replace('_', ' ').replace('.png', '').title()}</h3>
            <img src="{fig_name}" alt="{fig_name}">
        </div>
"""
        
        # Add risk metrics section if available
        if risk_metrics:
            html_content += """
        <h2>Risk Metrics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Description</th>
            </tr>
"""
            metrics_to_show = [
                ('Circuit Breaker', 'circuit_breaker_triggered', 'Trading halted if True'),
                ('Daily PnL', 'daily_pnl', 'Profit/Loss for current day'),
                ('Max Daily Loss', 'max_daily_loss', 'Maximum allowable daily loss'),
                ('Remaining Daily Loss', 'remaining_daily_loss', 'Remaining loss before circuit breaker'),
            ]
            
            for display_name, key, description in metrics_to_show:
                value = risk_metrics.get(key, 'N/A')
                if isinstance(value, bool):
                    value = 'ACTIVE' if value else 'INACTIVE'
                    css_class = 'metric-negative' if value == 'ACTIVE' else ''
                elif isinstance(value, (int, float)):
                    value = f"${value:.2f}" if abs(value) > 0.01 else f"{value}"
                
                html_content += f"""
            <tr>
                <td>{display_name}</td>
                <td class="{css_class if 'css_class' in locals() else ''}">{value}</td>
                <td>{description}</td>
            </tr>
"""
            html_content += """
        </table>
"""
        
        # Add comparison summary if available
        if comparison_data:
            html_content += f"""
        <h2>Strategy Comparison Summary</h2>
        <p>Latest comparison run: {comparison_data.get('timestamp', 'N/A')}</p>
        <p>Total symbols compared: {comparison_data.get('total_symbols', 0)}</p>
        
        <table>
            <tr>
                <th>Metric</th>
                <th>Pure Algorithmic</th>
                <th>HMM-Regime-Aware</th>
                <th>Difference</th>
            </tr>
"""
            if 'summary' in comparison_data:
                summary = comparison_data['summary']
                pure = summary.get('pure_algorithmic', {})
                hmm = summary.get('hmm_regime_aware', {})
                
                comparisons = [
                    ('Buy Signals', pure.get('buy', 0), hmm.get('buy', 0)),
                    ('Sell Signals', pure.get('sell', 0), hmm.get('sell', 0)),
                    ('Hold Signals', pure.get('hold', 0), hmm.get('hold', 0)),
                ]
                
                for name, pure_val, hmm_val in comparisons:
                    diff = hmm_val - pure_val
                    diff_str = f"+{diff}" if diff > 0 else str(diff)
                    html_content += f"""
            <tr>
                <td>{name}</td>
                <td>{pure_val}</td>
                <td>{hmm_val}</td>
                <td>{diff_str}</td>
            </tr>
"""
            
            html_content += """
        </table>
"""
        
        # Close HTML
        html_content += f"""
        <div class="timestamp">
            Report generated by Crypto Trading System Performance Dashboard
        </div>
    </div>
</body>
</html>
"""
        
        # Write HTML file
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        # Copy chart images to report directory
        for fig_file in fig_files:
            if os.path.exists(fig_file):
                import shutil
                shutil.copy(fig_file, output_dir)
        
        return html_file
    
    def _calculate_summary_stats(self, trades_df: Optional[pd.DataFrame],
                                risk_metrics: Dict[str, Any],
                                comparison_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics for report"""
        stats = {}
        
        # Trade statistics
        if trades_df is not None and len(trades_df) > 0:
            stats['total_trades'] = len(trades_df)
            
            if 'realized_pnl' in trades_df.columns:
                total_pnl = trades_df['realized_pnl'].sum()
                avg_trade_pnl = trades_df['realized_pnl'].mean()
                win_rate = (trades_df['realized_pnl'] > 0).mean()
                
                stats['total_pnl'] = total_pnl
                stats['total_pnl_formatted'] = f"{total_pnl:,.2f}"
                stats['pnl_class'] = 'metric-positive' if total_pnl > 0 else 'metric-negative'
                
                stats['avg_trade_pnl'] = avg_trade_pnl
                stats['avg_trade_pnl_formatted'] = f"{avg_trade_pnl:,.2f}"
                stats['avg_pnl_class'] = 'metric-positive' if avg_trade_pnl > 0 else 'metric-negative'
                
                stats['win_rate'] = win_rate
                stats['win_rate_formatted'] = f"{win_rate:.1%}"
                
                # Calculate Sharpe ratio (simplified)
                if 'realized_pnl_pct' in trades_df.columns and len(trades_df) > 1:
                    returns = trades_df['realized_pnl_pct'].dropna()
                    if len(returns) > 1:
                        sharpe = returns.mean() / (returns.std() + 1e-8) * np.sqrt(252)  # Annualized
                        stats['sharpe_ratio'] = sharpe
                        stats['sharpe_ratio_formatted'] = f"{sharpe:.2f}"
                
                # Calculate max drawdown
                if 'cumulative_pnl' in trades_df.columns:
                    cumulative = trades_df['cumulative_pnl'].values
                    running_max = np.maximum.accumulate(cumulative)
                    drawdown = (cumulative - running_max) / (running_max + 1e-8)
                    max_dd = drawdown.min()
                    stats['max_drawdown'] = max_dd
                    stats['max_drawdown_formatted'] = f"{max_dd:.1%}"
        
        # Risk metrics
        if risk_metrics:
            for key in ['total_trades', 'winning_trades', 'losing_trades', 'win_rate', 'total_pnl']:
                if key in risk_metrics:
                    stats[f'risk_{key}'] = risk_metrics[key]
        
        return stats
    
    def show_live_dashboard(self):
        """Display live dashboard (for development/testing)"""
        print(f"\n{'='*60}")
        print("LIVE PERFORMANCE DASHBOARD")
        print(f"{'='*60}")
        
        trades_df = self.load_trade_data()
        risk_metrics = self.load_risk_metrics()
        
        if trades_df is not None and len(trades_df) > 0:
            print(f"\nTrade Performance Summary:")
            print(f"  Total Trades: {len(trades_df)}")
            
            if 'realized_pnl' in trades_df.columns:
                total_pnl = trades_df['realized_pnl'].sum()
                win_rate = (trades_df['realized_pnl'] > 0).mean()
                print(f"  Total PnL: ${total_pnl:.2f}")
                print(f"  Win Rate: {win_rate:.1%}")
                
                # Show recent trades
                print(f"\nRecent Trades (last 5):")
                recent = trades_df.tail(5)
                for _, trade in recent.iterrows():
                    symbol = trade.get('symbol', 'N/A')
                    side = trade.get('side', 'N/A')
                    qty = trade.get('quantity', 0)
                    price = trade.get('price', 0)
                    pnl = trade.get('realized_pnl', 0)
                    print(f"  {trade.get('timestamp', 'N/A')}: {symbol} {side} {qty} @ ${price:.2f} (PnL: ${pnl:.2f})")
        else:
            print("\nNo trade data available. Run the trading engine to generate trades.")
        
        if risk_metrics:
            print(f"\nRisk Metrics:")
            print(f"  Circuit Breaker: {'ACTIVE' if risk_metrics.get('circuit_breaker_triggered', False) else 'INACTIVE'}")
            print(f"  Total PnL: ${risk_metrics.get('total_pnl', 0):.2f}")
            print(f"  Win Rate: {risk_metrics.get('win_rate', 0):.1%}")
            print(f"  Daily PnL: ${risk_metrics.get('daily_pnl', 0):.2f}")
        
        # Show comparison results
        comparison_data = self.load_latest_comparison()
        if comparison_data:
            print(f"\nLatest Strategy Comparison:")
            print(f"  Date: {comparison_data.get('timestamp', 'N/A')}")
            print(f"  Symbols: {comparison_data.get('total_symbols', 0)}")
            
            if 'summary' in comparison_data:
                summary = comparison_data['summary']
                print(f"  Agreement Rate: {summary.get('agreement_rate', 0):.1f}%")
                print(f"  Regime-Aware Count: {summary.get('regime_aware_count', 0)}")


def main():
    """Main function to run performance dashboard"""
    print("CRYPTO TRADING PERFORMANCE DASHBOARD")
    print("=" * 60)
    
    # Initialize dashboard
    dashboard = PerformanceDashboard()
    
    # Show live dashboard
    dashboard.show_live_dashboard()
    
    # Generate report automatically
    print("\nGenerating performance report...")
    report_file = dashboard.generate_performance_report()
    print(f"\nReport generated: {report_file}")
    
    # Try to open in browser
    try:
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(report_file)}")
        print("Opening report in browser...")
    except:
        print(f"Could not open browser. Please open the file manually: {report_file}")
    
    print("\n" + "=" * 60)
    print("Dashboard complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDashboard interrupted by user")
    except Exception as e:
        print(f"\nError in dashboard: {e}")
        import traceback
        traceback.print_exc()