#!/usr/bin/env python3
import re

def count():
    with open('src/data/mockProducts.ts', 'r', encoding='utf-8') as f:
        content = f.read()
    # Parse product blocks
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
                    products.append(block)
                    i = j + 1
                    break
            else:
                i += 1
        else:
            i += 1
    
    total_patterns = 0
    for block in products:
        name_match = re.search(r\"name:\\s*'([^']+)'\", block)
        name = name_match.group(1) if name_match else 'Unknown'
        # Count dp ids
        dp_ids = re.findall(r\"dp\\.id\\s*===\\s*'([^']+)'\", block)
        if dp_ids:
            print(f'{name}: {len(dp_ids)} patterns')
            total_patterns += len(dp_ids)
        else:
            print(f'{name}: 0 patterns')
    print(f'Total patterns across {len(products)} products: {total_patterns}')

if __name__ == '__main__':
    count()