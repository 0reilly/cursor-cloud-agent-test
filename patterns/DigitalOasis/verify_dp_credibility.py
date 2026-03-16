#!/usr/bin/env python3
"""
Verify credibility of dark pattern assignments in Patterns app mock data.
Categorize assignments as Confirmed, Plausible, or Questionable based on:
- Product category compatibility
- Known public documentation (FTC complaints, articles)
- Pattern definition alignment
"""
import re
import json
from typing import List, Dict, Tuple

def load_dark_patterns() -> Dict:
    """Load dark pattern definitions from mockDarkPatterns.ts"""
    with open('src/data/mockDarkPatterns.ts', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse dark pattern objects
    dp_pattern = r"{\s*id:\s*'([^']+)',[^}]*name:\s*'([^']+)',[^}]*description:\s*'([^']*)',"
    matches = re.findall(dp_pattern, content, re.DOTALL)
    
    dp_dict = {}
    for dp_id, name, desc in matches:
        # Clean description
        desc = re.sub(r'\s+', ' ', desc).strip()
        dp_dict[dp_id] = {'name': name, 'description': desc}
    
    return dp_dict

def load_product_assignments() -> List[Dict]:
    """Load product assignments from mockProducts.ts"""
    with open('src/data/mockProducts.ts', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all product objects
    # Each product starts with { id: '...', name: '...', ... }
    product_pattern = r"{\s*id:\s*'([^']+)',[^}]*?name:\s*'([^']+)',[^}]*?category:\s*'([^']+)',(?:[^}]|{[^}]*})*?darkPatterns:\s*\[(.*?)\]\s*,"
    matches = re.findall(product_pattern, content, re.DOTALL)
    
    products = []
    for prod_id, name, category, dp_block in matches:
        # Extract dp ids from the darkPatterns block
        dp_ids = re.findall(r"dp\.id\s*===\s*'([^']+)'", dp_block)
        products.append({
            'id': prod_id,
            'name': name,
            'category': category,
            'darkPatterns': dp_ids
        })
    
    return products

def categorize_assignments(products: List[Dict], dp_defs: Dict) -> Tuple[List, List, List]:
    """
    Categorize assignments based on heuristics and known patterns.
    Returns (confirmed, plausible, questionable)
    """
    confirmed = []
    plausible = []
    questionable = []
    
    # Known confirmed assignments (from previous web searches)
    confirmed_mapping = {
        'Instagram': ['dp5', 'dp8', 'dp6'],  # Fake notifications, confirmshaming, roach motel
        'Amazon': ['dp2', 'dp3', 'dp4', 'dp6'],  # Hidden costs, countdown, low stock, roach motel
        'TikTok': ['dp7', 'dp5'],  # Forced continuity (autoplay), addictive design
        'Netflix': ['dp1', 'dp6', 'dp7'],  # Misleading free trial, difficult cancellation
    }
    
    # Pattern compatibility by category
    category_compatibility = {
        'social_media': ['dp5', 'dp6', 'dp8', 'dp7', 'dp9'],  # dp7 for premium features
        'gaming': ['dp3', 'dp4', 'dp7', 'dp9'],  # dp7 questionable for free games
        'ecommerce': ['dp2', 'dp3', 'dp4', 'dp6', 'dp8'],
        'streaming': ['dp1', 'dp6', 'dp7', 'dp8'],
        'finance': ['dp9', 'dp2', 'dp7', 'dp8'],
        'productivity': ['dp6', 'dp7', 'dp8', 'dp4'],
        'dating': ['dp5', 'dp8', 'dp7', 'dp4'],
        'messaging': ['dp5', 'dp6', 'dp8', 'dp7'],
    }
    
    # Questionable pattern applications
    questionable_patterns = {
        'dp7': ['gaming', 'messaging', 'social_media'],  # Forced Continuity often misapplied
        'dp1': ['gaming', 'finance', 'productivity'],  # Misleading Free Trial should be for subscription services
    }
    
    for product in products:
        name = product['name']
        category = product['category']
        
        for dp_id in product['darkPatterns']:
            dp_name = dp_defs.get(dp_id, {}).get('name', 'Unknown')
            assignment = {
                'product': name,
                'category': category,
                'dp_id': dp_id,
                'dp_name': dp_name
            }
            
            # Check if confirmed by mapping
            if name in confirmed_mapping and dp_id in confirmed_mapping[name]:
                confirmed.append(assignment)
                continue
            
            # Check if questionable by pattern-category mismatch
            if dp_id in questionable_patterns and category in questionable_patterns[dp_id]:
                questionable.append(assignment)
                continue
            
            # Check category compatibility
            if category in category_compatibility:
                if dp_id in category_compatibility[category]:
                    plausible.append(assignment)
                else:
                    questionable.append(assignment)
            else:
                # Unknown category - default to plausible
                plausible.append(assignment)
    
    return confirmed, plausible, questionable

def main():
    print("=== Dark Pattern Assignment Credibility Verification ===\n")
    
    # Load data
    print("Loading dark pattern definitions...")
    dp_defs = load_dark_patterns()
    print(f"Found {len(dp_defs)} dark pattern definitions")
    
    print("\nLoading product assignments...")
    products = load_product_assignments()
    print(f"Found {len(products)} products")
    
    total_assignments = sum(len(p['darkPatterns']) for p in products)
    print(f"Total assignments: {total_assignments}")
    
    # Categorize
    print("\nCategorizing assignments...")
    confirmed, plausible, questionable = categorize_assignments(products, dp_defs)
    
    # Print results
    print(f"\n=== RESULTS ===")
    print(f"Confirmed: {len(confirmed)} assignments")
    print(f"Plausible: {len(plausible)} assignments")
    print(f"Questionable: {len(questionable)} assignments")
    
    # Show questionable assignments
    if questionable:
        print(f"\n=== QUESTIONABLE ASSIGNMENTS (review needed) ===")
        for q in questionable[:20]:  # Show first 20
            print(f"{q['product']} ({q['category']}): {q['dp_name']} ({q['dp_id']})")
        if len(questionable) > 20:
            print(f"... and {len(questionable) - 20} more")
    
    # Show confirmed assignments
    if confirmed:
        print(f"\n=== CONFIRMED ASSIGNMENTS ===")
        for c in confirmed[:10]:
            print(f"{c['product']}: {c['dp_name']}")
    
    # Save detailed report
    report = {
        'summary': {
            'total_products': len(products),
            'total_assignments': total_assignments,
            'confirmed': len(confirmed),
            'plausible': len(plausible),
            'questionable': len(questionable)
        },
        'confirmed_assignments': confirmed,
        'plausible_assignments': plausible[:100],  # Limit size
        'questionable_assignments': questionable,
        'dark_pattern_definitions': dp_defs
    }
    
    with open('dark_pattern_credibility_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nDetailed report saved to dark_pattern_credibility_report.json")
    
    # Generate recommendations
    print(f"\n=== RECOMMENDATIONS ===")
    if questionable:
        print("1. Review questionable assignments above for accuracy")
        print("2. Consider re-categorizing or removing mismatched patterns")
        print("3. Add documentation explaining data limitations")
    else:
        print("All assignments appear credible or plausible for mock data")
    
    # Check for free products with Misleading Free Trial (dp1)
    print(f"\n=== SPECIFIC CHECKS ===")
    free_products_with_dp1 = []
    for p in products:
        if 'dp1' in p['darkPatterns'] and p['category'] not in ['streaming', 'subscription']:
            free_products_with_dp1.append(p['name'])
    
    if free_products_with_dp1:
        print(f"Products with dp1 (Misleading Free Trial) that may not offer trials:")
        for name in free_products_with_dp1[:10]:
            print(f"  - {name}")
    else:
        print("No obvious mismatches for dp1 (Misleading Free Trial)")

if __name__ == '__main__':
    main()