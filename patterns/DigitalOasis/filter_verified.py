#!/usr/bin/env python3
"""
Filter dark patterns to only verified ones, add verification field.
"""
import re

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def find_matching_bracket(text, start_idx, open_char='[', close_char=']'):
    depth = 0
    for i in range(start_idx, len(text)):
        if text[i] == open_char:
            depth += 1
        elif text[i] == close_char:
            depth -= 1
            if depth == 0:
                return i
    return -1

def get_product_blocks(content):
    """Return list of (start, end, block) for each product in the array."""
    lines = content.split('\n')
    blocks = []
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
                    blocks.append((start, end, block))
                    i = j + 1
                    break
            else:
                i += 1
        else:
            i += 1
    return blocks

def extract_dark_patterns_array_from_block(block):
    """Return (start_idx, end_idx, array_text) of darkPatterns array within block."""
    match = re.search(r'darkPatterns:\s*\[', block)
    if not match:
        return None
    start = match.start()
    end = find_matching_bracket(block, start)
    if end == -1:
        return None
    return (start, end, block[start:end+1])

def parse_dark_pattern_entries(array_text):
    """Return list of dark pattern entry objects."""
    inner = array_text[array_text.find('[')+1:array_text.rfind(']')]
    entries = []
    brace = 0
    start = 0
    for i, ch in enumerate(inner):
        if ch == '{':
            brace += 1
        elif ch == '}':
            brace -= 1
            if brace == 0:
                obj_text = inner[start:i+1].strip()
                if obj_text:
                    entries.append(obj_text)
                start = i + 1
        elif ch == ',' and brace == 0:
            start = i + 1
    return entries

def parse_entry(entry):
    """Extract dp_id, prevalence, description."""
    dp_match = re.search(r"dp\.id\s*===\s*'([^']+)'", entry)
    prevalence_match = re.search(r"prevalence:\s*'([^']+)'", entry)
    desc_match = re.search(r"description:\s*'([^']*)'", entry)
    dp_id = dp_match.group(1) if dp_match else None
    prevalence = prevalence_match.group(1) if prevalence_match else None
    description = desc_match.group(1) if desc_match else ''
    return dp_id, prevalence, description, entry

def build_verification_mapping():
    """Return dict (product_name, dp_id) -> verification string."""
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
    # Add more as needed
    return mapping

def generate_verified_entry(dp_id, prevalence, description, verification):
    """Generate a new dark pattern entry with verification field."""
    # Escape single quotes in description
    desc_escaped = description.replace(\"'\", \"\\\\'\")
    return f'''    {{
      pattern: darkPatterns.find(dp => dp.id === '{dp_id}')!,
      prevalence: '{prevalence}',
      description: '{desc_escaped}',
      verification: '{verification}'
    }}'''

def process_block(block, mapping):
    """Return new block with only verified dark patterns."""
    # Extract product name
    name_match = re.search(r\"name:\\s*'([^']+)'\", block)
    if not name_match:
        return block
    product_name = name_match.group(1)
    
    # Find darkPatterns array
    array_info = extract_dark_patterns_array_from_block(block)
    if not array_info:
        return block
    start_idx, end_idx, array_text = array_info
    
    # Parse entries
    entries = parse_dark_pattern_entries(array_text)
    verified_entries = []
    for entry in entries:
        dp_id, prevalence, description, full_entry = parse_entry(entry)
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
    
    # Replace array in block
    new_block = block[:start_idx] + new_array_text + block[end_idx+1:]
    return new_block

def main():
    content = read_file('src/data/mockProducts.ts')
    mapping = build_verification_mapping()
    blocks = get_product_blocks(content)
    
    # Replace blocks from bottom to top
    lines = content.split('\n')
    for start, end, block in reversed(blocks):
        new_block = process_block(block, mapping)
        new_lines = new_block.split('\n')
        lines[start:end+1] = new_lines
    
    new_content = '\n'.join(lines)
    
    # Write backup
    write_file('src/data/mockProducts_backup.ts', content)
    # Write updated file
    write_file('src/data/mockProducts.ts', new_content)
    print(f'Processed {len(blocks)} products.')
    print('Backup saved to src/data/mockProducts_backup.ts')

if __name__ == '__main__':
    main()