#!/usr/bin/env python3
"""
Safely close the MKRUSD position.
"""
import sys
import time
from alpaca_client import AlpacaClient

def main():
    client = AlpacaClient()
    
    # Get account info
    account = client.get_account()
    if account:
        print(f"Account: {account['account_number']}")
        print(f"Cash: ${account['cash']:.2f}")
        print(f"Portfolio value: ${account['portfolio_value']:.2f}")
    
    # Get positions
    positions = client.get_positions()
    print(f"\nFound {len(positions)} positions:")
    
    for p in positions:
        print(f"  {p['symbol']}:")
        print(f"    Quantity: {p['qty']}")
        print(f"    Avg entry: ${p['avg_entry_price']:.2f}")
        print(f"    Current price: ${p['current_price']:.2f}")
        print(f"    Market value: ${p['market_value']:.2f}")
        print(f"    Unrealized PnL: ${p['unrealized_pl']:.2f} ({p['unrealized_plpc']:.2%})")
    
    # Close MKRUSD if exists
    for p in positions:
        if p['symbol'] == 'MKRUSD':
            print(f"\nAttempting to close MKRUSD position...")
            qty = float(p['qty'])
            current_price = float(p['current_price'])
            
            # Try limit order slightly below current price for quick fill
            limit_price = current_price * 0.995  # 0.5% below market
            
            print(f"  Quantity: {qty}")
            print(f"  Current price: ${current_price:.2f}")
            print(f"  Limit price: ${limit_price:.2f}")
            
            # Place limit sell order
            order = client.place_limit_order(
                symbol='MKRUSD',
                qty=qty,
                side='sell',
                limit_price=limit_price
            )
            
            if order:
                print(f"  Limit order placed: {order['id']}")
                print(f"  Status: {order['status']}")
                print(f"  Limit price: ${order.get('limit_price', 'N/A')}")
                
                # Wait a few seconds and check
                time.sleep(3)
                order_status = client.get_order(order['id'])
                if order_status:
                    print(f"  Updated status: {order_status['status']}")
                    if order_status['status'] == 'filled':
                        print(f"  Filled at avg price: ${order_status.get('filled_avg_price', 'N/A')}")
                    elif order_status['status'] == 'partially_filled':
                        print(f"  Partially filled: {order_status.get('filled_qty', 0)}")
                else:
                    print("  Could not retrieve order status")
            else:
                print("  Failed to place limit order")
                
                # Try market order as last resort
                print("\nTrying market order...")
                order = client.place_market_order('MKRUSD', qty, side='sell')
                if order:
                    print(f"  Market order placed: {order['id']}")
                else:
                    print("  Failed to place market order")
            break
    else:
        print("\nNo MKRUSD position found")

if __name__ == "__main__":
    main()