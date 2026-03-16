#!/usr/bin/env python3
"""
Add verification field to dark pattern entries in mockProducts.ts.
Simple line-by-line approach.
"""
import re

# Mapping of (product_name, dp_id) -> verification text
VERIFICATION_MAP = {
    ('Amazon', 'dp2'): 'FTC Complaint: Hidden costs in Amazon Prime case',
    ('Amazon', 'dp6'): 'FTC Complaint: Making Prime cancellation difficult (Roach Motel)',
    ('Amazon', 'dp7'): 'FTC Complaint: Tricking users into Prime subscriptions (Forced Continuity)',
    ('Fortnite', 'dp7'): 'FTC Settlement $245M: Unauthorized charges (Forced Continuity)',
    ('Robinhood', 'dp9'): 'MA Settlement $7.5M: Gamified manipulation',
    ('Uber', 'dp2'): 'Class Action Lawsuit: Hidden fees (drip pricing)',
    ('Uber', 'dp6'): 'FTC Action: Deceptive billing and cancellation practices (Roach Motel)',
    ('Uber', 'dp7'): 'FTC Action: Forced continuity in Uber One subscription',
    ('Instagram', 'dp8'): 'EU Complaint: Dark patterns to thwart AI opt-outs (noyb.eu)',
    ('TikTok', 'dp9'): 'EU Regulatory Action: Addictive design and infinite scroll',
    ('Candy Crush Saga', 'dp7'): 'Google Play Settlement (FTC): Unauthorized in-app purchases',
    ('Spotify', 'dp7'): 'FTC Complaint by Music Publishers: Deceptive conversion to bundled plans',
}

def main():
    with open('src/data/mockProducts.ts', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find product blocks: each product starts with '{' and ends with '},'
    # We'll track current product name
    i = 0
    current_product = None
    while i < len(lines):
        line = lines[i]
        # Look for product name line
        name_match = re.search(r"name:\s*'([^']+)'", line)
        if name_match:
            current_product = name_match.group(1)
        
        # Look for dark pattern entry line with pattern: darkPatterns.find(dp => dp.id === 'dpX')!
        dp_match = re.search(r"pattern:\s*darkPatterns\.find\(dp\s*=>\s*dp\.id\s*===\s*'([^']+)'\)!", line)
        if dp_match and current_product:
            dp_id = dp_match.group(1)
            key = (current_product, dp_id)
            verification = VERIFICATION_MAP.get(key)
            if verification:
                # Find the description line that follows (should be within same object)
                # We'll insert verification line after description line, before next property or closing brace
                # Search forward from current line
                j = i + 1
                while j < len(lines):
                    if lines[j].strip().startswith('description:'):
                        # Insert after this line
                        indent = len(lines[j]) - len(lines[j].lstrip())
                        new_line = ' ' * indent + f"verification: '{verification}',\n"
                        lines.insert(j + 1, new_line)
                        # Adjust indices because we added a line
                        i += 1
                        j += 1
                        break
                    if lines[j].strip() == '}' or lines[j].strip().startswith('prevalence:'):
                        # Should not happen, but fallback: insert before this line
                        indent = len(lines[j]) - len(lines[j].lstrip())
                        new_line = ' ' * indent + f"verification: '{verification}',\n"
                        lines.insert(j, new_line)
                        i += 1
                        j += 1
                        break
                    j += 1
        i += 1
    
    # Write backup
    with open('src/data/mockProducts_backup_before_verification.ts', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    # Write updated file
    with open('src/data/mockProducts.ts', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("Added verification fields.")

if __name__ == '__main__':
    main()