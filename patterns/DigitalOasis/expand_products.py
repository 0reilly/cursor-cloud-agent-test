#!/usr/bin/env python3
import json

# Dark pattern IDs
dark_patterns = [f'dp{i}' for i in range(1, 10)]
# Side effect IDs
side_effects = [f'se{i}' for i in range(1, 9)]

# Categories from type definition
categories = ['social_media', 'ecommerce', 'productivity', 'gaming', 'streaming', 'dating', 'finance']

# List of popular apps/services with category mapping
apps = [
    # Social Media (expand beyond existing)
    ('Twitter', 'social_media', 'Social networking service for short messages called tweets.', '🐦'),
    ('Snapchat', 'social_media', 'Multimedia messaging app with disappearing content.', '👻'),
    ('Pinterest', 'social_media', 'Image sharing and social media service for saving and discovering information.', '📌'),
    ('Reddit', 'social_media', 'Social news aggregation, web content rating, and discussion website.', '🤖'),
    ('WhatsApp', 'social_media', 'Cross-platform centralized instant messaging and voice-over-IP service.', '💬'),
    ('Discord', 'social_media', 'Voice, video and text communication service for communities.', '🎮'),
    ('Telegram', 'social_media', 'Cloud-based instant messaging and voice-over-IP service.', '📨'),
    ('Signal', 'social_media', 'Cross-platform encrypted messaging service.', '🔒'),
    ('WeChat', 'social_media', 'Chinese multi-purpose messaging, social media and mobile payment app.', '👥'),
    ('Clubhouse', 'social_media', 'Drop-in audio chat app for conversations.', '🎤'),
    ('Threads', 'social_media', 'Text-based conversation app from Meta.', '🧵'),
    ('Bluesky', 'social_media', 'Decentralized social network from former Twitter team.', '☁️'),
    ('Mastodon', 'social_media', 'Decentralized social networking platform.', '🐘'),
    
    # Ecommerce (beyond Amazon/eBay)
    ('Alibaba', 'ecommerce', 'Chinese multinational technology company specializing in e-commerce.', '🏮'),
    ('Shopify', 'ecommerce', 'E-commerce platform for online stores and retail point-of-sale systems.', '🛒'),
    ('Walmart', 'ecommerce', 'American multinational retail corporation.', '🛍️'),
    ('Target', 'ecommerce', 'American retail corporation.', '🎯'),
    ('Etsy', 'ecommerce', 'E-commerce website focused on handmade or vintage items and craft supplies.', '✂️'),
    ('Wish', 'ecommerce', 'Mobile e-commerce platform that connects customers with merchants.', '⭐'),
    ('AliExpress', 'ecommerce', 'Chinese online retail service.', '📦'),
    ('Best Buy', 'ecommerce', 'American multinational consumer electronics retailer.', '📺'),
    ('Newegg', 'ecommerce', 'Online retailer of computer hardware and consumer electronics.', '💻'),
    ('Wayfair', 'ecommerce', 'American e-commerce company that sells furniture and home goods.', '🛋️'),
    ('Zalando', 'ecommerce', 'European online fashion platform.', '👠'),
    ('ASOS', 'ecommerce', 'British online fashion and cosmetic retailer.', '👗'),
    
    # Streaming (beyond Netflix/Spotify)
    ('Hulu', 'streaming', 'Subscription streaming service offering films and television series.', '📺'),
    ('Disney+', 'streaming', 'American subscription video on-demand over-the-top streaming service.', '🏰'),
    ('HBO Max', 'streaming', 'American subscription video on-demand streaming service.', '🎬'),
    ('Apple TV+', 'streaming', 'Subscription streaming service by Apple Inc.', '📱'),
    ('YouTube Premium', 'streaming', 'Subscription service offering ad-free YouTube and original content.', '📹'),
    ('Amazon Prime Video', 'streaming', 'Amazon\'s streaming video service.', '🎥'),
    ('Twitch', 'streaming', 'Video live streaming service for gamers.', '🟣'),
    ('Crunchyroll', 'streaming', 'American subscription video on-demand service for anime.', '🍥'),
    ('Paramount+', 'streaming', 'Subscription streaming service from Paramount Global.', '🌌'),
    ('Peacock', 'streaming', 'American streaming service from NBCUniversal.', '🦚'),
    
    # Gaming (beyond Fortnite/Candy Crush)
    ('Minecraft', 'gaming', 'Sandbox video game developed by Mojang Studios.', '🧱'),
    ('Roblox', 'gaming', 'Online game platform and game creation system.', '🧩'),
    ('Call of Duty Mobile', 'gaming', 'Free-to-play shooter game in the Call of Duty franchise.', '🔫'),
    ('PUBG Mobile', 'gaming', 'Battle royale mobile game.', '🎯'),
    ('Among Us', 'gaming', 'Online multiplayer social deduction game.', '👨‍🚀'),
    ('Clash of Clans', 'gaming', 'Freemium mobile strategy video game.', '⚔️'),
    ('Clash Royale', 'gaming', 'Freemium real-time strategy video game.', '👑'),
    ('Pokémon GO', 'gaming', 'Augmented reality mobile game.', '🐾'),
    ('Genshin Impact', 'gaming', 'Action role-playing game with gacha mechanics.', '⚔️'),
    ('League of Legends', 'gaming', 'Multiplayer online battle arena video game.', '⚡'),
    ('Valorant', 'gaming', 'Free-to-play first-person tactical hero shooter.', '🎭'),
    ('Apex Legends', 'gaming', 'Free-to-play battle royale-hero shooter.', '🔥'),
    ('Steam', 'gaming', 'Video game digital distribution service.', '🎮'),
    ('Epic Games Store', 'gaming', 'Digital video game storefront.', '🛒'),
    
    # Finance (beyond Robinhood)
    ('PayPal', 'finance', 'Online payment system supporting online money transfers.', '💳'),
    ('Venmo', 'finance', 'Mobile payment service owned by PayPal.', '💰'),
    ('Cash App', 'finance', 'Mobile payment service developed by Square.', '💵'),
    ('Coinbase', 'finance', 'Cryptocurrency exchange platform.', '₿'),
    ('Acorns', 'finance', 'Financial technology company that invests spare change.', '🌰'),
    ('Chime', 'finance', 'Financial technology company providing banking services.', '🏦'),
    ('Mint', 'finance', 'Personal finance management service.', '🌿'),
    ('YNAB', 'finance', 'Personal budgeting software.', '📊'),
    ('TurboTax', 'finance', 'Tax preparation software.', '📑'),
    ('Credit Karma', 'finance', 'Personal finance company.', '💳'),
    ('NerdWallet', 'finance', 'Personal finance company.', '👓'),
    ('Bloomberg', 'finance', 'Financial, software, data, and media company.', '📈'),
    
    # Dating (beyond Tinder)
    ('Bumble', 'dating', 'Dating app where women make the first move.', '🐝'),
    ('Hinge', 'dating', 'Dating app designed to be deleted.', '🔗'),
    ('OkCupid', 'dating', 'American online dating, friendship, and social networking platform.', '💘'),
    ('Match.com', 'dating', 'Online dating website.', '❤️'),
    ('Plenty of Fish', 'dating', 'Online dating service.', '🐟'),
    ('Grindr', 'dating', 'Geosocial networking and online dating app for LGBTQ+ people.', '🌈'),
    ('HER', 'dating', 'Dating app for LGBTQ+ women and queer people.', '👭'),
    ('Coffee Meets Bagel', 'dating', 'Dating platform that sends curated matches daily.', '☕'),
    ('eHarmony', 'dating', 'Online dating website.', '💍'),
    
    # Productivity (beyond Slack/Strava)
    ('Microsoft Teams', 'productivity', 'Business communication platform.', '💼'),
    ('Zoom', 'productivity', 'Video conferencing platform.', '📹'),
    ('Asana', 'productivity', 'Work management platform.', '📋'),
    ('Trello', 'productivity', 'Web-based list-making application.', '📝'),
    ('Notion', 'productivity', 'Project management and note-taking software.', '📓'),
    ('Evernote', 'productivity', 'Note-taking app.', '📒'),
    ('Google Workspace', 'productivity', 'Cloud-based productivity and collaboration tools.', '🔧'),
    ('Microsoft Office', 'productivity', 'Suite of productivity applications.', '📎'),
    ('ClickUp', 'productivity', 'Productivity platform for task management.', '⬆️'),
    ('Monday.com', 'productivity', 'Work operating system.', '📅'),
    ('Basecamp', 'productivity', 'Project management and team communication software.', '⛺'),
    ('Todoist', 'productivity', 'Task management app.', '✅'),
]

# Start with existing 15 products (we'll keep them)
# We'll generate new products with IDs starting from 16
existing_count = 15
new_products = []

for idx, (name, category, description, icon) in enumerate(apps, start=existing_count + 1):
    # Assign some dark patterns based on category
    dark_pattern_entries = []
    if category == 'social_media':
        dark_pattern_entries = [
            {'pattern_id': 'dp5', 'prevalence': 'common', 'desc': 'Fake activity notifications create FOMO.'},
            {'pattern_id': 'dp7', 'prevalence': 'ubiquitous', 'desc': 'Infinite scroll encourages addictive usage.'},
        ]
    elif category == 'ecommerce':
        dark_pattern_entries = [
            {'pattern_id': 'dp3', 'prevalence': 'common', 'desc': 'Countdown timers create false urgency.'},
            {'pattern_id': 'dp4', 'prevalence': 'common', 'desc': 'Low stock messages pressure purchases.'},
            {'pattern_id': 'dp2', 'prevalence': 'common', 'desc': 'Hidden costs in checkout.'},
        ]
    elif category == 'streaming':
        dark_pattern_entries = [
            {'pattern_id': 'dp1', 'prevalence': 'common', 'desc': 'Free trial auto-converts to paid subscription.'},
            {'pattern_id': 'dp6', 'prevalence': 'common', 'desc': 'Complex cancellation process.'},
            {'pattern_id': 'dp7', 'prevalence': 'ubiquitous', 'desc': 'Auto-play next episode forces continued watching.'},
        ]
    elif category == 'gaming':
        dark_pattern_entries = [
            {'pattern_id': 'dp7', 'prevalence': 'ubiquitous', 'desc': 'Forces in-app purchases to progress.'},
            {'pattern_id': 'dp4', 'prevalence': 'common', 'desc': 'Limited-time items create artificial scarcity.'},
            {'pattern_id': 'dp9', 'prevalence': 'medium', 'desc': 'Gamified manipulation encourages spending.'},
        ]
    elif category == 'finance':
        dark_pattern_entries = [
            {'pattern_id': 'dp9', 'prevalence': 'common', 'desc': 'Gamified interface encourages risky behavior.'},
            {'pattern_id': 'dp2', 'prevalence': 'common', 'desc': 'Hidden fees or commission structures.'},
        ]
    elif category == 'dating':
        dark_pattern_entries = [
            {'pattern_id': 'dp5', 'prevalence': 'ubiquitous', 'desc': 'Fake activity notifications about profile views.'},
            {'pattern_id': 'dp8', 'prevalence': 'common', 'desc': 'Shames users for not upgrading to premium.'},
        ]
    elif category == 'productivity':
        dark_pattern_entries = [
            {'pattern_id': 'dp7', 'prevalence': 'common', 'desc': 'Forces constant availability through notifications.'},
            {'pattern_id': 'dp4', 'prevalence': 'common', 'desc': 'Urgent notification badges create workplace anxiety.'},
        ]
    
    # Assign side effects
    side_effect_ids = []
    if category == 'social_media':
        side_effect_ids = ['se1', 'se2', 'se7']  # anxiety, sleep disruption, addiction
    elif category == 'ecommerce':
        side_effect_ids = ['se5', 'se8']  # compulsive spending, decision fatigue
    elif category == 'streaming':
        side_effect_ids = ['se2', 'se7', 'se8']  # sleep disruption, addiction, decision fatigue
    elif category == 'gaming':
        side_effect_ids = ['se7', 'se5', 'se1']  # addiction, compulsive spending, anxiety
    elif category == 'finance':
        side_effect_ids = ['se5', 'se1', 'se7']  # compulsive spending, anxiety, addiction
    elif category == 'dating':
        side_effect_ids = ['se1', 'se6', 'se7']  # anxiety, social isolation, addiction
    elif category == 'productivity':
        side_effect_ids = ['se1', 'se3', 'se8']  # anxiety, attention fragmentation, decision fatigue
    
    # Transparency score: lower for social media, higher for productivity
    transparency_score = {
        'social_media': 20,
        'ecommerce': 45,
        'streaming': 65,
        'gaming': 30,
        'finance': 40,
        'dating': 35,
        'productivity': 75,
    }.get(category, 50)
    
    # Tags
    tags = []
    if category == 'social_media':
        tags = ['social', 'networking', 'communication']
    elif category == 'ecommerce':
        tags = ['shopping', 'retail', 'marketplace']
    elif category == 'streaming':
        tags = ['video', 'music', 'entertainment']
    elif category == 'gaming':
        tags = ['mobile', 'pc', 'console', 'addictive']
    elif category == 'finance':
        tags = ['money', 'investing', 'banking']
    elif category == 'dating':
        tags = ['relationships', 'social', 'premium']
    elif category == 'productivity':
        tags = ['work', 'tools', 'organization']
    
    # Build product object
    product = {
        'id': f'product{idx}',
        'name': name,
        'category': category,
        'description': description,
        'darkPatterns': [
            {
                'pattern': f"darkPatterns.find(dp => dp.id === '{dp['pattern_id']}')!",
                'prevalence': dp['prevalence'],
                'description': dp['desc']
            }
            for dp in dark_pattern_entries
        ],
        'sideEffects': [f"sideEffects.find(se => se.id === '{se_id}')!" for se_id in side_effect_ids],
        'transparencyScore': transparency_score,
        'icon': icon,
        'studies': f"getStudiesForProduct('{name}')",
        'tags': tags
    }
    new_products.append(product)

# Output TypeScript code for the new products
print('// New products generated by expand_products.py')
for product in new_products:
    print('  {')
    print(f'    id: \'{product["id"]}\',')
    print(f'    name: \'{product["name"]}\',')
    print(f'    category: \'{product["category"]}\',')
    print(f'    description: \'{product["description"]}\',')
    print('    darkPatterns: [')
    for dp in product['darkPatterns']:
        print('      {')
        print(f'        pattern: {dp["pattern"]},')
        print(f'        prevalence: \'{dp["prevalence"]}\',')
        print(f'        description: \'{dp["description"]}\'')
        print('      },')
    print('    ],')
    print('    sideEffects: [')
    for se in product['sideEffects']:
        print(f'      {se},')
    print('    ],')
    print(f'    transparencyScore: {product["transparencyScore"]},')
    print(f'    icon: \'{product["icon"]}\',')
    print(f'    studies: {product["studies"]},')
    print(f'    tags: {json.dumps(product["tags"])}')
    print('  },')