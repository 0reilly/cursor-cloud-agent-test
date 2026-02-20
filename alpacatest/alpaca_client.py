"""
Alpaca API Client for Crypto Trading
"""

import alpaca_trade_api as tradeapi
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from typing import Optional, Dict, List, Any

from config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlpacaClient:
    """Client for interacting with Alpaca API for crypto trading"""
    
    def __init__(self):
        """Initialize Alpaca API connection"""
        try:
            self.api = tradeapi.REST(
                ALPACA_API_KEY,
                ALPACA_SECRET_KEY,
                ALPACA_BASE_URL,
                api_version='v2'
            )
            logger.info("Alpaca API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca API: {e}")
            raise
    
    # ============ ACCOUNT METHODS ============
    
    def get_account(self) -> Optional[Dict[str, Any]]:
        """Get account information"""
        try:
            account = self.api.get_account()
            return {
                'id': account.id,
                'account_number': account.account_number,
                'status': account.status,
                'currency': account.currency,
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'equity': float(account.equity),
                'buying_power': float(account.buying_power),
                'daytrade_count': account.daytrade_count,
                'trading_blocked': account.trading_blocked,
                'transfers_blocked': account.transfers_blocked,
                'account_blocked': account.account_blocked,
                'created_at': account.created_at,
                'last_equity': float(account.last_equity) if account.last_equity else None,
                'long_market_value': float(account.long_market_value) if account.long_market_value else None,
                'short_market_value': float(account.short_market_value) if account.short_market_value else None,
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            return None
    
    def get_account_summary(self) -> str:
        """Get formatted account summary"""
        account = self.get_account()
        if not account:
            return "Unable to get account information"
        
        return (
            f"Account: {account['account_number']} ({account['status']})\n"
            f"Cash: ${account['cash']:,.2f}\n"
            f"Buying Power: ${account['buying_power']:,.2f}\n"
            f"Portfolio Value: ${account['portfolio_value']:,.2f}\n"
            f"Equity: ${account['equity']:,.2f}\n"
            f"Day Trades: {account['daytrade_count']}/3\n"
            f"Blocked: Trading={account['trading_blocked']}, Transfers={account['transfers_blocked']}"
        )
    
    # ============ POSITION METHODS ============
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        try:
            positions = self.api.list_positions()
            return [
                {
                    'symbol': pos.symbol,
                    'asset_id': pos.asset_id,
                    'asset_class': pos.asset_class,
                    'exchange': pos.exchange,
                    'qty': float(pos.qty),
                    'market_value': float(pos.market_value),
                    'current_price': float(pos.current_price),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                    'side': pos.side,
                    'unrealized_intraday_pl': float(pos.unrealized_intraday_pl) if pos.unrealized_intraday_pl else None,
                    'unrealized_intraday_plpc': float(pos.unrealized_intraday_plpc) if pos.unrealized_intraday_plpc else None,
                }
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get specific position by symbol"""
        try:
            position = self.api.get_position(symbol)
            return {
                'symbol': position.symbol,
                'qty': float(position.qty),
                'market_value': float(position.market_value),
                'current_price': float(position.current_price),
                'avg_entry_price': float(position.avg_entry_price),
                'unrealized_pl': float(position.unrealized_pl),
                'unrealized_plpc': float(position.unrealized_plpc),
            }
        except Exception as e:
            # Position not found
            return None
    
    def close_position(self, symbol: str, qty: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Close a position (full or partial)"""
        try:
            if qty:
                # Close partial position
                position = self.get_position(symbol)
                if not position:
                    logger.error(f"No position found for {symbol}")
                    return None
                
                # Determine side (sell for long, buy for short)
                side = 'sell' if position['qty'] > 0 else 'buy'
                qty = abs(qty)
                
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    type='market',
                    time_in_force='gtc'
                )
            else:
                # Close entire position
                order = self.api.close_position(symbol)
            
            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': order.qty,
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'filled_at': order.filled_at,
                'filled_avg_price': order.filled_avg_price,
            }
        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")
            return None
    
    def close_all_positions(self) -> List[Dict[str, Any]]:
        """Close all positions"""
        positions = self.get_positions()
        results = []
        
        for position in positions:
            logger.info(f"Closing position: {position['symbol']} ({position['qty']} shares)")
            result = self.close_position(position['symbol'])
            if result:
                results.append(result)
                time.sleep(0.5)  # Small delay between orders
        
        return results
    
    # ============ MARKET DATA METHODS ============
    
    def get_market_data(self, symbol: str, timeframe: str = "5Min", limit: int = 100) -> pd.DataFrame:
        """Get historical market data for crypto"""
        try:
            # Convert timeframe string to TimeFrame object
            from alpaca_trade_api.rest import TimeFrame, TimeFrameUnit
            
            tf_mapping = {
                "1Min": TimeFrame(1, TimeFrameUnit.Minute),
                "5Min": TimeFrame(5, TimeFrameUnit.Minute),
                "15Min": TimeFrame(15, TimeFrameUnit.Minute),
                "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
                "1Day": TimeFrame(1, TimeFrameUnit.Day),
            }
            
            tf = tf_mapping.get(timeframe, TimeFrame(5, TimeFrameUnit.Minute))
            
            # Get crypto bars
            bars = self.api.get_crypto_bars([symbol], tf, limit=limit)
            df = bars.df
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            # Reset index and clean up
            df.reset_index(inplace=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Calculate additional metrics
            df['returns'] = df['close'].pct_change()
            df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            
            logger.info(f"Retrieved {len(df)} bars for {symbol} ({timeframe})")
            return df
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a crypto symbol"""
        try:
            # Get latest trade
            trades = self.api.get_latest_crypto_trades([symbol])
            if trades and len(trades) > 0:
                return float(trades[0].price)
            return None
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def get_bid_ask(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get bid/ask spread for crypto"""
        try:
            quote = self.api.get_latest_crypto_quote([symbol])
            if quote and len(quote) > 0:
                return {
                    'bid': float(quote[0].bp),
                    'ask': float(quote[0].ap),
                    'bid_size': float(quote[0].bs),
                    'ask_size': float(quote[0].as_),
                    'timestamp': quote[0].t,
                }
            return None
        except Exception as e:
            logger.error(f"Error getting bid/ask for {symbol}: {e}")
            return None
    
    # ============ ORDER METHODS ============
    
    def place_order(self, symbol: str, qty: float, side: str, 
                   order_type: str = 'market', limit_price: Optional[float] = None,
                   stop_price: Optional[float] = None, time_in_force: str = 'gtc') -> Optional[Dict[str, Any]]:
        """Place a trading order"""
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force,
                limit_price=limit_price,
                stop_price=stop_price
            )
            
            logger.info(f"Order placed: {order.id} - {side} {qty} {symbol} ({order_type})")
            
            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': order.qty,
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'filled_at': order.filled_at,
                'filled_avg_price': order.filled_avg_price,
                'limit_price': order.limit_price,
                'stop_price': order.stop_price,
                'time_in_force': order.time_in_force,
                'created_at': order.created_at,
            }
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def place_market_order(self, symbol: str, qty: float, side: str) -> Optional[Dict[str, Any]]:
        """Place a market order (convenience method)"""
        return self.place_order(symbol, qty, side, 'market')
    
    def place_limit_order(self, symbol: str, qty: float, side: str, limit_price: float) -> Optional[Dict[str, Any]]:
        """Place a limit order"""
        return self.place_order(symbol, qty, side, 'limit', limit_price=limit_price)
    
    def place_stop_order(self, symbol: str, qty: float, side: str, stop_price: float) -> Optional[Dict[str, Any]]:
        """Place a stop order"""
        return self.place_order(symbol, qty, side, 'stop', stop_price=stop_price)
    
    def place_stop_limit_order(self, symbol: str, qty: float, side: str, 
                              limit_price: float, stop_price: float) -> Optional[Dict[str, Any]]:
        """Place a stop-limit order"""
        return self.place_order(symbol, qty, side, 'stop_limit', 
                               limit_price=limit_price, stop_price=stop_price)
    
    def get_orders(self, status: str = 'all', limit: int = 50) -> List[Dict[str, Any]]:
        """Get order history"""
        try:
            orders = self.api.list_orders(status=status, limit=limit)
            return [
                {
                    'id': order.id,
                    'symbol': order.symbol,
                    'qty': order.qty,
                    'side': order.side,
                    'type': order.type,
                    'status': order.status,
                    'filled_at': order.filled_at,
                    'filled_avg_price': order.filled_avg_price,
                    'limit_price': order.limit_price,
                    'stop_price': order.stop_price,
                    'time_in_force': order.time_in_force,
                    'created_at': order.created_at,
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            self.api.cancel_order(order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def cancel_all_orders(self) -> List[str]:
        """Cancel all open orders"""
        try:
            self.api.cancel_all_orders()
            logger.info("All orders cancelled")
            return []
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return []
    
    # ============ ASSET METHODS ============
    
    def get_available_crypto(self) -> List[Dict[str, Any]]:
        """Get available crypto assets"""
        try:
            assets = self.api.list_assets(status='active')
            crypto_assets = []
            
            for asset in assets:
                raw = asset._raw
                if raw.get('class') == 'crypto' and raw.get('tradable', False):
                    crypto_assets.append({
                        'symbol': raw['symbol'],
                        'name': raw['name'],
                        'exchange': raw['exchange'],
                        'status': raw['status'],
                        'tradable': raw['tradable'],
                        'marginable': raw.get('marginable', False),
                        'shortable': raw.get('shortable', False),
                        'easy_to_borrow': raw.get('easy_to_borrow', False),
                    })
            
            return crypto_assets
        except Exception as e:
            logger.error(f"Error getting crypto assets: {e}")
            return []
    
    def is_market_open(self) -> bool:
        """Check if crypto market is open (always True for crypto)"""
        # Crypto markets trade 24/7
        return True
    
    def is_asset_active(self, symbol: str) -> bool:
        """Check if a crypto asset is active and tradable"""
        try:
            # Get asset from Alpaca
            asset = self.api.get_asset(symbol)
            raw = asset._raw
            # Check if asset is crypto, active, and tradable
            return raw.get('class') == 'crypto' and raw.get('status') == 'active' and raw.get('tradable', False)
        except Exception as e:
            logger.warning(f"Error checking asset status for {symbol}: {e}")
            # If we can't get asset info, assume inactive
            return False
    
    # ============ PORTFOLIO METHODS ============
    
    def get_portfolio_history(self, period: str = '1M') -> pd.DataFrame:
        """Get portfolio history"""
        try:
            history = self.api.get_portfolio_history(period=period)
            df = history.df
            
            if df.empty:
                return pd.DataFrame()
            
            # Calculate additional metrics
            df['returns'] = df['equity'].pct_change()
            df['cumulative_returns'] = (1 + df['returns']).cumprod() - 1
            
            return df
        except Exception as e:
            logger.error(f"Error getting portfolio history: {e}")
            return pd.DataFrame()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        account = self.get_account()
        positions = self.get_positions()
        
        if not account:
            return {}
        
        total_unrealized_pl = sum(pos.get('unrealized_pl', 0) for pos in positions)
        total_market_value = sum(pos.get('market_value', 0) for pos in positions)
        
        return {
            'equity': account['equity'],
            'cash': account['cash'],
            'portfolio_value': account['portfolio_value'],
            'total_unrealized_pl': total_unrealized_pl,
            'total_market_value': total_market_value,
            'num_positions': len(positions),
            'daytrade_count': account['daytrade_count'],
        }


# ============ TEST FUNCTIONS ============

def test_connection():
    """Test the Alpaca connection"""
    print("Testing Alpaca connection...")
    
    try:
        client = AlpacaClient()
        
        # Test account
        account = client.get_account()
        if account:
            print(f"✅ Connection successful!")
            print(f"Account: {account['account_number']}")
            print(f"Cash: ${account['cash']:,.2f}")
            print(f"Portfolio Value: ${account['portfolio_value']:,.2f}")
        else:
            print("❌ Failed to get account")
            return False
        
        # Test market data
        print("\nTesting market data...")
        btc_data = client.get_market_data("BTC/USD", timeframe="5Min", limit=5)
        if not btc_data.empty:
            print(f"✅ Got {len(btc_data)} BTC bars")
            print(f"Latest: {btc_data.iloc[-1]['close']:.2f}")
        else:
            print("❌ Failed to get market data")
        
        # Test positions
        print("\nTesting positions...")
        positions = client.get_positions()
        print(f"Found {len(positions)} positions")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()