#!/usr/bin/env python3
import re
import json

# Read the mockProducts.ts file
with open('src/data/mockProducts.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# First, let's extract all dark pattern definitions from mockDarkPatterns.ts
with open('src/data/mockDarkPatterns.ts', 'r', encoding='utf-8') as f:
    dp_content = f.read()

# Extract dp definitions
dp_pattern = r"{\s*id: '([^']+)',[\s\S]*?name: '([^']+)',[\s\S]*?description: '([^']*)',"
dp_matches = re.findall(dp_pattern, dp_content)
dp_dict = {dp_id: {'name': name, 'description': desc} for dp_id, name, desc in dp_matches}

print(f"Found {len(dp_dict)} dark pattern definitions:")
for dp_id, info in dp_dict.items():
    print(f"  {dp_id}: {info['name']}")

# Now extract product-dark pattern assignments
# Pattern: name: 'ProductName', ... darkPatterns: [ ... pattern: darkPatterns.find(dp => dp.id === 'dpX')! ... ]
product_pattern = r"name: '([^']+)',[\s\S]*?darkPatterns: \[([\s\S]*?)\]\s*,"

# Simpler approach: find all product blocks
product_blocks = re.findall(r"{\s*id: '[^']+',\s*name: '([^']+)',[\s\S]*?darkPatterns: \[([\s\S]*?)\]\s*,", content)

print(f"\nFound {len(product_blocks)} products with dark pattern assignments")

# Analyze each product
product_assignments = {}
for product_name, dp_block in product_blocks:
    # Find all dp.id references
    dp_ids = re.findall(r"dp\.id === '([^']+)'", dp_block)
    product_assignments[product_name] = dp_ids

# Print summary
print("\nProduct dark pattern assignments:")
for product, dp_ids in list(product_assignments.items())[:10]:  # First 10
    dp_names = [dp_dict.get(dp_id, {}).get('name', 'UNKNOWN') for dp_id in dp_ids]
    print(f"{product}: {', '.join(dp_names)}")

# Count total assignments
total_assignments = sum(len(dp_ids) for dp_ids in product_assignments.values())
print(f"\nTotal dark pattern assignments: {total_assignments}")

# Check for any products without dark patterns
products_without = [p for p, dp_ids in product_assignments.items() if len(dp_ids) == 0]
if products_without:
    print(f"\nProducts WITHOUT dark patterns: {len(products_without)}")
    for p in products_without[:10]:
        print(f"  {p}")
else:
    print("\nAll products have at least one dark pattern assigned.")

# Save to JSON for manual review
with open('dark_pattern_analysis.json', 'w', encoding='utf-8') as f:
    json.dump({
        'dark_pattern_definitions': dp_dict,
        'product_assignments': product_assignments
    }, f, indent=2)

print("\nAnalysis saved to dark_pattern_analysis.json")