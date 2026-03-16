import { categories, products } from '../src/data';
import type { DigitalProduct, Category } from '../src/types';

console.log('Checking category-product mapping...');
console.log('Total categories:', categories.length);
console.log('Total products:', products.length);

let allMatch = true;
for (const category of categories) {
    const matchingProducts = products.filter((p: DigitalProduct) => p.category === category.id);
    console.log(`\nCategory: ${category.name} (${category.id})`);
    console.log(`  Expected productCount: ${category.productCount}`);
    console.log(`  Actual matching products: ${matchingProducts.length}`);
    if (matchingProducts.length !== category.productCount) {
        console.log(`  MISMATCH! Difference: ${matchingProducts.length - category.productCount}`);
        allMatch = false;
    }
    // List product names if mismatch
    if (matchingProducts.length === 0) {
        console.log('  No products found for this category!');
    }
}

console.log('\n--- Checking SearchScreen filter logic ---');
// Simulate activeCategory filter
const activeCategory = 'social_media';
const filtered = products.filter((p: DigitalProduct) => !activeCategory || p.category === activeCategory);
console.log(`Active category '${activeCategory}': ${filtered.length} products`);

// Simulate search query
const searchQuery = 'Instagram';
const filteredSearch = products.filter((p: DigitalProduct) => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.tags.some((tag: string) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
);
console.log(`Search query '${searchQuery}': ${filteredSearch.length} products`);

if (allMatch) {
    console.log('\n✅ All category product counts match.');
} else {
    console.log('\n❌ Some mismatches found.');
    process.exit(1);
}