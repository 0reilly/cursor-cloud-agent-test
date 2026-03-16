#!/usr/bin/env python3
import re
import json

with open('src/data/mockProducts.ts', 'r', encoding='utf-8') as f:
    lines = f.readlines()

products = []
current = {}
in_product = False
in_dark_patterns = False
in_side_effects = False
brace_count = 0
dp_block = ''

# Simple stateful parser
i = 0
while i < len(lines):
    line = lines[i].strip()
    if line.startswith('{') and 'id:' in line and not in_product:
        # start of product object
        in_product = True
        current = {'id': '', 'name': '', 'category': '', 'darkPatterns': []}
        brace_count = 1
        # extract id
        id_match = re.search(r"id:\s*'([^']+)'", line)
        if id_match:
            current['id'] = id_match.group(1)
        # extract name
        name_match = re.search(r"name:\s*'([^']+)'", line)
        if name_match:
            current['name'] = name_match.group(1)
        # extract category
        cat_match = re.search(r"category:\s*'([^']+)'", line)
        if cat_match:
            current['category'] = cat_match.group(1)
        i += 1
        continue
    if in_product:
        # count braces
        brace_count += line.count('{') - line.count('}')
        if brace_count == 0:
            # end of product
            products.append(current)
            in_product = False
            continue
        # look for darkPatterns array
        if 'darkPatterns:' in line:
            # start of array
            dp_block = line
            # continue until array ends (closing bracket)
            while i < len(lines) and ']' not in dp_block:
                i += 1
                dp_block += lines[i]
            # extract dp ids
            dp_ids = re.findall(r"dp\.id === '([^']+)'", dp_block)
            current['darkPatterns'] = dp_ids
        # note: we could also capture sideEffects, etc.
    i += 1

print(f'Parsed {len(products)} products')

# Load dark pattern definitions
with open('src/data/mockDarkPatterns.ts', 'r', encoding='utf-8') as f:
    dp_content = f.read()
dp_matches = re.findall(r"{\s*id: '([^']+)',[\s\S]*?name: '([^']+)',[\s\S]*?description: '([^']*)',", dp_content)
dp_dict = {dp_id: {'name': name, 'description': desc} for dp_id, name, desc in dp_matches}
print(f'Dark patterns: {len(dp_dict)}')

# Categorize assignments
questionable = []
plausible = []
confirmed = []

# Heuristics: map of pattern id to questionable categories
# dp7 (Forced Continuity) likely misapplied to free games with IAP (not unauthorized charging)
# dp9 (Gamified Manipulation) plausible for gaming, financial apps
# dp5 (Fake Activity Notifications) plausible for social media
# dp6 (Roach Motel) plausible for subscription services
# dp1 (Misleading Free Trial) only for products with free trials
# dp2 (Hidden Costs) for e-commerce, subscriptions
# dp3 (Countdown Timer) for e-commerce, travel
# dp4 (Low Stock Messages) for e-commerce
# dp8 (Confirmshaming) for many

# We'll flag based on category mismatch
category_to_patterns = {
    'social_media': ['dp5', 'dp6', 'dp8', 'dp7'],  # dp7 maybe for paid features
    'gaming': ['dp9', 'dp4', 'dp3', 'dp7'],  # dp7 questionable
    'ecommerce': ['dp2', 'dp3', 'dp4', 'dp6', 'dp8'],
    'streaming': ['dp1', 'dp6', 'dp7', 'dp8'],
    'finance': ['dp9', 'dp2', 'dp7'],
    'productivity': ['dp6', 'dp7', 'dp8'],
    'dating': ['dp5', 'dp8', 'dp7'],
    'messaging': ['dp5', 'dp6', 'dp8', 'dp7'],
}

# For each product, evaluate each assignment
for p in products:
    cat = p['category']
    for dp in p['darkPatterns']:
        # check if dp is defined
        if dp not in dp_dict:
            print(f'Warning: {p[\"name\"]} has unknown dp {dp}')
            continue
        # For now, mark all as plausible (we will later upgrade based on search)
        plausible.append({'product': p['name'], 'category': cat, 'dp': dp, 'dp_name': dp_dict[dp]['name']})

print(f'Total assignments: {sum(len(p[\"darkPatterns\"]) for p in products)}')
print(f'Plausible (pre-search): {len(plausible)}')

# Save for manual review
with open('assignment_review.json', 'w', encoding='utf-8') as f:
    json.dump({
        'products': products,
        'dark_patterns': dp_dict,
        'plausible_assignments': plausible
    }, f, indent=2)

print('Saved to assignment_review.json')