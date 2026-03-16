#!/usr/bin/env python3
import re
import json

with open('src/data/mockProducts.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# Split by product objects (assuming each product ends with '},')
# This is fragile but works for the file
blocks = re.split(r'\n\s*},\s*\n', content)
print(f'Found {len(blocks)} blocks')

products = []
for block in blocks:
    # Extract id, name, category
    id_match = re.search(r"id:\s*'([^']+)'", block)
    name_match = re.search(r"name:\s*'([^']+)'", block)
    category_match = re.search(r"category:\s*'([^']+)'", block)
    if not name_match:
        continue
    product = {
        'id': id_match.group(1) if id_match else '',
        'name': name_match.group(1),
        'category': category_match.group(1) if category_match else '',
        'darkPatterns': []
    }
    # Find darkPatterns array
    dp_start = block.find('darkPatterns:')
    if dp_start == -1:
        continue
    # Find the closing bracket of the array
    substr = block[dp_start:]
    bracket_count = 0
    i = 0
    while i < len(substr):
        ch = substr[i]
        if ch == '[':
            bracket_count += 1
        elif ch == ']':
            bracket_count -= 1
            if bracket_count == 0:
                # end of array
                dp_block = substr[:i+1]
                break
        i += 1
    else:
        dp_block = substr
    # Extract dp ids
    dp_ids = re.findall(r"dp\.id === '([^']+)'", dp_block)
    product['darkPatterns'] = dp_ids
    products.append(product)

print(f'Extracted {len(products)} products')

# Load dark patterns
with open('src/data/mockDarkPatterns.ts', 'r', encoding='utf-8') as f:
    dp_content = f.read()
dp_matches = re.findall(r"id:\s*'([^']+)'[^}]*name:\s*'([^']+)'[^}]*description:\s*'([^']*)'", dp_content, re.DOTALL)
dp_dict = {}
for dp_id, name, desc in dp_matches:
    # Clean up description (remove newlines)
    desc = re.sub(r'\s+', ' ', desc).strip()
    dp_dict[dp_id] = {'name': name, 'description': desc}

print(f'Dark patterns: {len(dp_dict)}')
for dp_id, info in dp_dict.items():
    print(f'  {dp_id}: {info[\"name\"]}')

# Count assignments
total = sum(len(p['darkPatterns']) for p in products)
print(f'Total assignments: {total}')

# Save for review
with open('product_assignments_detailed.json', 'w', encoding='utf-8') as f:
    json.dump({'products': products, 'dark_patterns': dp_dict}, f, indent=2)

print('Saved to product_assignments_detailed.json')

# Generate summary CSV
print('\nProduct,Category,Assigned Patterns')
for p in products[:30]:  # first 30
    dp_names = [dp_dict.get(dp, {}).get('name', dp) for dp in p['darkPatterns']]
    print(f'{p[\"name\"]},{p[\"category\"]},\"{dp_names}\"')