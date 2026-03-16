#!/usr/bin/env python3
import re
import json

# Read the mockProducts.ts file
with open('src/data/mockProducts.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# Brand name to simple-icons slug mapping
# Some brands need special mapping
brand_to_slug = {
    'Instagram': 'instagram',
    'Amazon': 'amazon',
    'TikTok': 'tiktok',
    'Netflix': 'netflix',
    'Uber': 'uber',
    'Candy Crush Saga': 'king',  # King makes Candy Crush
    'Tinder': 'tinder',
    'LinkedIn': 'linkedin',
    'Spotify': 'spotify',
    'Facebook': 'facebook',
    'Slack': 'slack',
    'Strava': 'strava',
    'eBay': 'ebay',
    'Fortnite': 'epicgames',  # Epic Games makes Fortnite
    'Robinhood': 'robinhood',
    'Twitter': 'twitter',
    'Snapchat': 'snapchat',
    'Pinterest': 'pinterest',
    'Reddit': 'reddit',
    'WhatsApp': 'whatsapp',
    'Discord': 'discord',
    'Telegram': 'telegram',
    'Signal': 'signal',
    'WeChat': 'wechat',
    'Clubhouse': 'clubhouse',
    'Threads': 'threads',  # Meta's Threads
    'Bluesky': 'bluesky',
    'Mastodon': 'mastodon',
    'Tumblr': 'tumblr',
    'VK': 'vk',
    'QQ': 'tencentqq',
    'Sina Weibo': 'sinaweibo',
    'Line': 'line',
    'Viber': 'viber',
    'Skype': 'skype',
    'Alibaba': 'alibaba',
    'Shopify': 'shopify',
    'Walmart': 'walmart',
    'Target': 'target',
    'Etsy': 'etsy',
    'Wish': 'wish',
    'AliExpress': 'aliexpress',
    'Best Buy': 'bestbuy',
    'Newegg': 'newegg',
    'Wayfair': 'wayfair',
    'Zalando': 'zalando',
    'ASOS': 'asos',
    'JD.com': 'jd',
    'Rakuten': 'rakuten',
    # Add more mappings as needed
}

# Function to generate logo URL
def get_logo_url(brand_name):
    # Default: convert to lowercase, remove spaces and special chars
    slug = brand_to_slug.get(brand_name)
    if not slug:
        # Generate slug: lowercase, remove spaces, special chars
        slug = brand_name.lower().replace(' ', '').replace('.', '').replace('-', '')
    return f'https://cdn.simpleicons.org/{slug}/white'

# Parse and replace icons
lines = content.split('\n')
output_lines = []
i = 0

while i < len(lines):
    line = lines[i]
    output_lines.append(line)
    
    # Check for product name line
    if 'name:' in line and 'product' not in line.lower():
        name_match = re.search(r"name: '([^']+)'", line)
        if name_match:
            brand_name = name_match.group(1)
            # Look ahead for icon line (usually within next 20 lines)
            for j in range(i+1, min(i+20, len(lines))):
                if 'icon:' in lines[j]:
                    icon_match = re.search(r"icon: '([^']+)'", lines[j])
                    if icon_match:
                        # Replace the icon line
                        old_icon_line = lines[j]
                        logo_url = get_logo_url(brand_name)
                        new_icon_line = f"    icon: '{logo_url}',"
                        # Replace in output
                        output_lines[-1] = new_icon_line
                        # Skip the original icon line when we get to it
                        i = j
                        break
    i += 1

# Write back to file
with open('src/data/mockProducts.ts', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print(f'Updated {len(brand_to_slug)} product logos')