#!/usr/bin/env python3
"""
Filter dark patterns to only verified ones, keep original entries.
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
    return (start, end, block[start:end+1])

def parse_dark_pattern_entries(array_text):
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
    dp_match = re.search(r"dp\.id\s*===\s*'([^']+)'", entry)
    dp_id = dp_match.group(1) if dp_match else None
    return dp_id, entry

def build_verification_mapping():
    mapping = {}
    # FTC ACTIONS
    mapping[('Amazon', 'dp2')] = True
    mapping[('Amazon', 'dp6')] = True
    mapping[('Amazon', 'dp7')] = True
    mapping[('Fortnite', 'dp7')] = True
    mapping[('Robinhood', 'dp9')] = True
    # Uber
    mapping[('Uber', 'dp2')] = True
    mapping[('Uber', 'dp6')] = True
    mapping[('Uber', 'dp7')] = True
    # Instagram
    mapping[('Instagram', 'dp8')] = True
    # TikTok
    mapping[('TikTok', 'dp9')] = True
    # Candy Crush Saga
    mapping[('Candy Crush Saga', 'dp7')] = True
    # Spotify
    mapping[('Spotify', 'dp7')] = True
    # Add more as needed
    return mapping

def process_block(block, mapping):
    name_match = re.search(r"name:\s*'([^']+)'", block)
    if not name_match:
        return block
    product_name = name_match.group(1)
    
    array_info = extract_dark_patterns_array_from_block(block)
    if not array_info:
        return block
    start_idx, end_idx, array_text = array_info
    
    entries = parse_dark_pattern_entries(array_text)
    verified_entries = []
    for entry in entries:
        dp_id, full_entry = parse_entry(entry)
        if dp_id is None:
            continue
        if mapping.get((product_name, dp_id)):
            verified_entries.append(full_entry)
    
    if verified_entries:
        new_array_text = '  darkPatterns: [\n' + ',\n'.join(verified_entries) + '\n  ],'
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
    
    write_file('src/data/mockProducts_backup.ts', content)
    write_file('src/data/mockProducts.ts', new_content)
    print(f'Processed {len(blocks)} products.')
    print('Backup saved to src/data/mockProducts_backup.ts')
    print('Updated src/data/mockProducts.ts with only verified dark patterns.')

if __name__ == '__main__':
    main()