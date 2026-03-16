require('ts-node/register');
const { categories, products } = require('../src/data');

console.log('Categories:', categories.length);
console.log('Products:', products.length);

let mismatches = [];
categories.forEach(cat => {
    const count = products.filter(p => p.category === cat.id).length;
    console.log(`${cat.id}: expected ${cat.productCount}, actual ${count}`);
    if (count !== cat.productCount) {
        mismatches.push({ cat, count });
    }
});
if (mismatches.length) {
    console.log('\nMISMATCHES:', mismatches);
} else {
    console.log('\nAll counts match!');
}

// Check for categories with zero products
const zeroCategories = categories.filter(cat => products.filter(p => p.category === cat.id).length === 0);
console.log('\nCategories with zero products:', zeroCategories.map(c => c.id).join(', ') || 'none');