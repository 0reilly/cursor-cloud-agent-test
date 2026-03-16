#!/usr/bin/env python3
"""
Apply verification to mockProducts.ts, keeping only verified dark patterns.
Adds verification field.
"""
import re
import json

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def find_matching_bracket(text, start_idx, open_char='[', close_char=']'):
    """Return index of matching closing bracket."""
    depth = 0
    for i in range(start_idx, len(text)):
        if text[i] == open_char:
            depth += 1
        elif text[i] == close_char:
            depth -= 1
            if depth == 0:
                return i
    return -1

def extract_dark_patterns_array(product_block):
    """Return (start_idx, end_idx, array_text) of darkPatterns array."""
    match = re.search(r'darkPatterns:\s*\[', product_block)
    if not match:
        return None
    start = match.start()
    end = find_matching_bracket(product_block, start)
    if end == -1:
        return None
    # Include the closing bracket
    return (start, end, product_block[start:end+1])

def parse_dark_pattern_entries(array_text):
    """Parse each entry in darkPatterns array."""
    # Remove leading 'darkPatterns: [' and trailing ']'
    inner = array_text[array_text.find('[')+1:array_text.rfind(']')]
    entries = []
    # Split by '},' but careful about nested braces
    brace = 0
    start = 0
    for i, ch in enumerate(inner):
        if ch == '{':
            brace += 1
        elif ch == '}':
            brace -= 1
            if brace == 0:
                # End of object
                obj_text = inner[start:i+1].strip()
                if obj_text:
                    entries.append(obj_text)
                start = i + 1
        elif ch == ',' and brace == 0:
            start = i + 1
    return entries

def parse_pattern_entry(entry):
    """Extract dp_id, prevalence, description from an entry."""
    dp_match = re.search(r"dp\.id\s*===\s*'([^']+)'", entry)
    prevalence_match = re.search(r"prevalence:\s*'([^']+)'", entry)
    desc_match = re.search(r"description:\s*'([^']*)'", entry)
    dp_id = dp_match.group(1) if dp_match else None
    prevalence = prevalence_match.group(1) if prevalence_match else None
    description = desc_match.group(1) if desc_match else ''
    return dp_id, prevalence, description

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
    return mapping

def generate_verified_entry(dp_id, prevalence, description, verification):
    """Generate a new dark pattern entry with verification field."""
    # Ensure description escaped single quotes
    desc_escaped = description.replace(\"'\", \"\\\\'\")
    return f'''    {{
      pattern: darkPatterns.find(dp => dp.id === '{dp_id}')!,
      prevalence: '{prevalence}',
      description: '{desc_escaped}',
      verification: '{verification}'
    }}'''

def process_product_block(block, mapping):
    """Return new block with verified dark patterns only."""
    # Extract product name
    name_match = re.search(r\"name:\\s*'([^']+)'\", block)
    if not name_match:
        return block
    product_name = name_match.group(1)
    
    # Find darkPatterns array
    array_info = extract_dark_patterns_array(block)
    if not array_info:
        return block
    start_idx, end_idx, array_text = array_info
    
    # Parse entries
    entries = parse_dark_pattern_entries(array_text)
    verified_entries = []
    for entry in entries:
        dp_id, prevalence, description = parse_pattern_entry(entry)
        if dp_id is None:
            continue
        verification = mapping.get((product_name, dp_id))
        if verification:
            verified_entries.append(generate_verified_entry(dp_id, prevalence, description, verification))
    
    # Build new array text
    if verified_entries:
        new_array_text = '  darkPatterns: [\n' + ',\n'.join(verified_entries) + '\n  ],'
    else:
        new_array_text = '  darkPatterns: [],'
    
    # Replace the array in block
    new_block = block[:start_idx] + new_array_text + block[end_idx+1:]
    return new_block

def split_products(content):
    """Split content into individual product blocks."""
    # Find the start of the products array
    lines = content.split('\n')
    products = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith('{'):
            start = i
            brace_count = 0
            for j in range(i, len(lines)):
                line = lines[j]
                brace_count += line.count('{')
                brace_count -= line.count('}')
                if brace_count == 0 and line.strip().endswith('},'):
                    end = j
                    block = '\n'.join(lines[start:end+1])
                    products.append((start, end, block))
                    i = j + 1
                    break
            else:
                i += 1
        else:
            i += 1
    return lines, products

def main():
    content = read_file('src/data/mockProducts.ts')
    mapping = build_verification_mapping()
    
    lines, products = split_products(content)
    # We'll rebuild the file by replacing each product block
    # Since blocks are contiguous and non-overlapping, we can replace from bottom to top
    # But easier: reconstruct entire file by iterating lines and replacing blocks.
    # We'll create a new lines list
    new_lines = lines.copy()
    # Replace from bottom to top to avoid index shifting
    for start, end, block in reversed(products):
        new_block = process_product_block(block, mapping)
        # Replace lines[start:end+1] with new_block split
        new_block_lines = new_block.split('\n')
        new_lines[start:end+1] = new_block_lines
    
    new_content = '\n'.join(new_lines)
    
    # Write backup
    write_file('src/data/mockProducts_backup.ts', content)
    # Write new file
    write_file('src/data/mockProducts.ts', new_content)
    print(f'Processed {len(products)} products.')
    print('Backup saved to mockProducts_backup.ts')
    print('Updated mockProducts.ts')

if __name__ == '__main__':
    main()