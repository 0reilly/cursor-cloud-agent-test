const fs = require('fs');
const path = require('path');

const mockPath = path.join(__dirname, 'src/data/mockProducts.ts');
const content = fs.readFileSync(mockPath, 'utf8');
const lines = content.split('\n');

// Header: everything before first export line
let firstExportIdx = -1;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('export const products: DigitalProduct[] = [')) {
    firstExportIdx = i;
    break;
  }
}
if (firstExportIdx === -1) throw new Error('No export line found');
const headerLines = lines.slice(0, firstExportIdx); // lines before export
console.log(`Header lines: ${headerLines.length}`);

// Find all export lines
const exportIndices = [];
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('export const products: DigitalProduct[] = [')) {
    exportIndices.push(i);
  }
}
console.log(`Export arrays at lines: ${exportIndices}`);

// Use the third export array (index 2) as original products
if (exportIndices.length < 3) {
  throw new Error('Expected at least three export arrays');
}
const originalStart = exportIndices[2];
console.log(`Original array start line: ${originalStart}`);

// Find matching closing bracket for original array
let bracketCount = 0;
let originalEnd = -1;
// locate opening bracket on start line
const startLineText = lines[originalStart];
const eqIdx = startLineText.indexOf('= ');
const openBracketIdx = startLineText.indexOf('[', eqIdx);
if (openBracketIdx === -1) throw new Error('Opening bracket not found');
// iterate lines starting from originalStart
for (let i = originalStart; i < lines.length; i++) {
  const line = lines[i];
  const startJ = (i === originalStart) ? openBracketIdx : 0;
  for (let j = startJ; j < line.length; j++) {
    const ch = line[j];
    if (ch === '[') bracketCount++;
    if (ch === ']') bracketCount--;
    if (bracketCount === 0) {
      originalEnd = i;
      break;
    }
  }
  if (originalEnd !== -1) break;
}
if (originalEnd === -1) throw new Error('Could not find matching closing bracket');
console.log(`Original array end line: ${originalEnd}`);

// Extract inner lines of original array (excluding brackets)
const originalInnerLines = lines.slice(originalStart + 1, originalEnd);
const originalInner = originalInnerLines.join('\n');

// Read new products
const newProductsPath = path.join(__dirname, 'new_products.txt');
let newProducts = fs.readFileSync(newProductsPath, 'utf8').trim();
if (newProducts.endsWith(',')) newProducts = newProducts.slice(0, -1);

// Build new array
const newArray = `export const products: DigitalProduct[] = [\n${originalInner}\n${newProducts}\n];`;
const defaultExport = '\n\nexport default products;';
const newContent = headerLines.join('\n') + '\n' + newArray + defaultExport;

fs.writeFileSync(mockPath, newContent);
console.log('Created clean mockProducts.ts with original 15 + new 85 products');
console.log('Total products:', originalInnerLines.filter(l => l.trim().startsWith('id:')).length + 85);
