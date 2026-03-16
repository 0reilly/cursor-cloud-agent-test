#!/usr/bin/env python3
"""
Generate verified mockProducts.ts with only legally confirmed dark patterns.
Adds verification_source field.
"""
import re
import json

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def parse_products(content):
    """Parse TypeScript product array into list of dicts with positions."""
    # Find the start of the products array
    lines = content.split('\n')
    products = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith('{'):
            start = i
            brace_count = 0
            # Parse until matching '},'
            for j in range(i, len(lines)):
                line = lines[j]
                brace_count += line.count('{')
                brace_count -= line.count('}')
                if brace_count == 0 and line.strip().endswith('},'):
                    end = j
                    # Extract block
                    block = '\n'.join(lines[start:end+1])
                    products.append({
                        'start': start,
                        'end': end,
                        'block': block,
                        'lines': lines[start:end+1]
                    })
                    i = j + 1
                    break
            else:
                i += 1
        else:
            i += 1
    return lines, products

def extract_product_info(block):
    """Extract name and dark patterns from a product block."""
    # Extract name
    name_match = re.search(r"name:\s*'([^']+)'", block)
    name = name_match.group(1) if name_match else None
    # Extract dark patterns array
    dp_match = re.search(r'darkPatterns:\s*\[(.*?)\]\s*,', block, re.DOTALL)
    if not dp_match:
        return name, []
    dp_content = dp_match.group(1)
    # Find each pattern assignment
    pattern_re = r"pattern:\s*darkPatterns\.find\(dp\s*=>\s*dp\.id\s*===\s*'([^']+)'\)"
    dp_ids = re.findall(pattern_re, dp_content)
    return name, dp_ids

def build_verification_mapping():
    """Return mapping (product_name, dp_id) -> verification string."""
    mapping = {}
    # FTC ACTIONS
    mapping[('Amazon', 'dp2')] = 'FTC Complaint: Hidden costs in Amazon Prime case'
    mapping[('Amazon', 'dp6')] = 'FTC Complaint: Making Prime cancellation difficult (Roach Motel)'
    mapping[('Amazon', 'dp7')] = 'FTC Complaint: Tricking users into Prime subscriptions (Forced Continuity)'
    mapping[('Fortnite', 'dp7')] = 'FTC Settlement $245M: Unauthorized charges (Forced Continuity)'
    mapping[('Robinhood', 'dp9')] = 'MA Settlement $7.5M: Gamified manipulation'
    # Uber
    mapping[('Uber', 'dp2')] = 'Class Action Lawsuit: Hidden fees (drip pricing)'
    mapping[('Uber', 'dp6')] = 'FTC Action: Deceptive billing and cancellation practices (Roach Motel)'
    mapping[('Uber', 'dp7')] = 'FTC Action: Forced continuity in Uber One subscription'
    # Instagram
    mapping[('Instagram', 'dp8')] = 'EU Complaint: Dark patterns to thwart AI opt-outs (noyb.eu)'
    # TikTok
    mapping[('TikTok', 'dp9')] = 'EU Regulatory Action: Addictive design and infinite scroll'
    # Candy Crush Saga
    mapping[('Candy Crush Saga', 'dp7')] = 'Google Play Settlement (FTC): Unauthorized in-app purchases'
    # Spotify
    mapping[('Spotify', 'dp7')] = 'FTC Complaint by Music Publishers: Deceptive conversion to bundled plans'
    # Netflix (no legal action, but keep as universally acknowledged?)
    # mapping[('Netflix', 'dp1')] = 'Industry Standard: Streaming services known for misleading free trials'
    # Add more as needed
    return mapping

def verify_pattern(product_name, dp_id, mapping):
    return mapping.get((product_name, dp_id))

def generate_new_block(block, mapping):
    """Replace darkPatterns array with verified patterns only."""
    lines = block.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect start of darkPatterns array
        if 'darkPatterns:' in line and lines[i+1].strip().startswith('['):
            # Collect the entire array
            array_start = i
            # Find matching closing bracket
            brace = 0
            for j in range(i, len(lines)):
                brace += lines[j].count('[')
                brace -= lines[j].count(']')
                if brace == 0:
                    array_end = j
                    break
            else:
                array_end = len(lines) - 1
            # Extract product name from block (already known)
            product_name = re.search(r"name:\s*'([^']+)'", block).group(1)
            # Build new darkPatterns array
            new_array = []
            # Parse existing patterns
            # We'll just replace the whole array with verified patterns
            # For simplicity, we'll keep only verified patterns
            # We'll need to keep the original pattern objects with verification field
            # This is complex; we'll implement later
            # For now, we'll just comment out and replace with empty array
            new_lines.append(line)  # keep 'darkPatterns: ['
            new_lines.append('    // Verified patterns will be inserted')
            new_lines.append('  ],')
            i = array_end + 1
            continue
        new_lines.append(line)
        i += 1
    return '\n'.join(new_lines)

def main():
    content = read_file('src/data/mockProducts.ts')
    lines, products = parse_products(content)
    mapping = build_verification_mapping()
    
    # For each product, print name and patterns
    for prod in products:
        name, dp_ids = extract_product_info(prod['block'])
        print(f'{name}: {dp_ids}')
    
    # TODO: implement replacement

if __name__ == '__main__':
    main()