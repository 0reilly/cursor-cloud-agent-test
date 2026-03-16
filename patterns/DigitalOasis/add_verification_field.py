#!/usr/bin/env python3
"""
Add verification field to dark pattern entries.
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
    match = re.search(r'darkPatterns:\s*\[', block)
    if not match:
        return None
    start = match.start()
    end = find_matching_bracket(block, start)
    if end == -1:
        return None
    if end + 1 < len(block) and block[end + 1] == ',':
        end += 1
    return (start, end, block[start:end+1])

def parse_dark_pattern_entries(array_text):
    prefix = 'darkPatterns: ['
    if array_text.startswith(prefix):
        inner = array_text[len(prefix):]
    else:
        inner = array_text
    if inner.endswith('],'):
        inner = inner[:-2]
    elif inner.endswith(']'):
        inner = inner[:-1]
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
    dp_match = re.search(r\"dp\\.id\\s*===\\s*'([^']+)'\", entry)
    dp_id = dp_match.group(1) if dp_match else None
    return dp_id, entry

def build_verification_mapping():
    mapping = {}
    mapping[('Amazon', 'dp2')] = 'FTC Complaint: Hidden costs in Amazon Prime case'
    mapping[('Amazon', 'dp6')] = 'FTC Complaint: Making Prime cancellation difficult (Roach Motel)'
    mapping[('Amazon', 'dp7')] = 'FTC Complaint: Tricking users into Prime subscriptions (Forced Continuity)'
    mapping[('Fortnite', 'dp7')] = 'FTC Settlement $245M: Unauthorized charges (Forced Continuity)'
    mapping[('Robinhood', 'dp9')] = 'MA Settlement $7.5M: Gamified manipulation'
    mapping[('Uber', 'dp2')] = 'Class Action Lawsuit: Hidden fees (drip pricing)'
    mapping[('Uber', 'dp6')] = 'FTC Action: Deceptive billing and cancellation practices (Roach Motel)'
    mapping[('Uber', 'dp7')] = 'FTC Action: Forced continuity in Uber One subscription'
    mapping[('Instagram', 'dp8')] = 'EU Complaint: Dark patterns to thwart AI opt-outs (noyb.eu)'
    mapping[('TikTok', 'dp9')] = 'EU Regulatory Action: Addictive design and infinite scroll'
    mapping[('Candy Crush Saga', 'dp7')] = 'Google Play Settlement (FTC): Unauthorized in-app purchases'
    mapping[('Spotify', 'dp7')] = 'FTC Complaint by Music Publishers: Deceptive conversion to bundled plans'
    return mapping

def add_verification_to_entry(entry, verification):
    # Insert verification line before closing brace
    lines = entry.split('\n')
    new_lines = []
    for line in lines:
        new_lines.append(line)
        if line.strip().startswith('description:'):
            # Add verification line after description line, with same indentation
            indent = len(line) - len(line.lstrip())
            new_lines.append(' ' * indent + f\"verification: '{verification}'\")
    # If we didn't find description (should not happen), append before closing brace
    if len(new_lines) == len(lines):
        # Find the line with '}' and insert before it
        for i, line in enumerate(lines):
            if line.strip() == '}':
                indent = len(line) - len(line.lstrip())
                lines.insert(i, ' ' * indent + f\"verification: '{verification}'\")
                break
        new_lines = lines
    return '\n'.join(new_lines)

def process_block(block, mapping):
    name_match = re.search(r\"name:\\s*'([^']+)'\", block)
    if not name_match:
        return block
    product_name = name_match.group(1)
    
    array_info = extract_dark_patterns_array_from_block(block)
    if not array_info:
        return block
    start_idx, end_idx, array_text = array_info
    
    entries = parse_dark_pattern_entries(array_text)
    new_entries = []
    for entry in entries:
        dp_id, full_entry = parse_entry(entry)
        if dp_id is None:
            new_entries.append(full_entry)
            continue
        verification = mapping.get((product_name, dp_id))
        if verification:
            new_entries.append(add_verification_to_entry(full_entry, verification))
        else:
            new_entries.append(full_entry)
    
    if new_entries:
        new_array_text = '  darkPatterns: [\n' + ',\n'.join(new_entries) + '\n  ],'
    else:
        new_array_text = '  darkPatterns: [],'
    
    new_block = block[:start_idx] + new_array_text + block[end_idx+1:]
    return new_block

def main():
    content = read_file('src/data/mockProducts.ts')
    mapping = build_verification_mapping()
    blocks = get_product_blocks(content)
    
    lines = content.split('\n')
    for start, end, block in reversed(blocks):
        new_block = process_block(block, mapping)
        new_lines = new_block.split('\n')
        lines[start:end+1] = new_lines
    
    new_content = '\n'.join(lines)
    
    write_file('src/data/mockProducts_backup3.ts', content)
    write_file('src/data/mockProducts.ts', new_content)
    print(f'Added verification fields to {len(blocks)} products.')

if __name__ == '__main__':
    main()