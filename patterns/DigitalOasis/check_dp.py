#!/usr/bin/env python3
import re

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

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

content = read_file('src/data/mockProducts.ts')
blocks = get_product_blocks(content)

mapping = {
    ('Amazon', 'dp2'): True,
    ('Amazon', 'dp6'): True,
    ('Amazon', 'dp7'): True,
    ('Fortnite', 'dp7'): True,
    ('Robinhood', 'dp9'): True,
    ('Uber', 'dp2'): True,
    ('Uber', 'dp6'): True,
    ('Uber', 'dp7'): True,
    ('Instagram', 'dp8'): True,
    ('TikTok', 'dp9'): True,
    ('Candy Crush Saga', 'dp7'): True,
    ('Spotify', 'dp7'): True,
}

for start, end, block in blocks:
    name_match = re.search(r"name:\s*'([^']+)'", block)
    if not name_match:
        continue
    product_name = name_match.group(1)
    # find darkPatterns array
    dp_match = re.search(r'darkPatterns:\s*\[', block)
    if dp_match:
        # count entries
        entries = re.findall(r"pattern:\s*darkPatterns\.find\(dp\s*=>\s*dp\.id\s*===\s*'([^']+)'\)!", block)
        if entries:
            print(f'{product_name}: {len(entries)} entries')
            for dp_id in entries:
                key = (product_name, dp_id)
                if key in mapping:
                    print(f'  - {dp_id} verified')
                else:
                    print(f'  - {dp_id} NOT verified')
        else:
            # check if empty array
            if re.search(r'darkPatterns:\s*\[\s*\]', block):
                print(f'{product_name}: empty')
            else:
                print(f'{product_name}: unknown format')