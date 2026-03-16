const fs = require('fs');
const path = require('path');

// Since we can't directly import TypeScript, we'll read and parse the files
// This is a simplified parser for our specific data format

function exportProducts() {
  const filePath = path.join(__dirname, '../src/data/mockProducts.ts');
  let content = fs.readFileSync(filePath, 'utf8');
  
  // Remove imports and helper functions
  // Find the products array
  const start = content.indexOf('export const products: DigitalProduct[] = [');
  if (start === -1) {
    throw new Error('Could not find products export');
  }
  
  // Find matching bracket
  let bracketCount = 0;
  let end = start;
  for (let i = start; i < content.length; i++) {
    if (content[i] === '[') bracketCount++;
    if (content[i] === ']') bracketCount--;
    if (bracketCount === 0) {
      end = i + 1;
      break;
    }
  }
  
  const arrayContent = content.substring(start, end);
  // Extract just the array
  const arrayMatch = arrayContent.match(/\[[\s\S]*\]/);
  if (!arrayMatch) {
    throw new Error('Could not extract array');
  }
  
  let arrayStr = arrayMatch[0];
  
  // Clean up TypeScript annotations
  arrayStr = arrayStr
    .replace(/\/\/.*$/gm, '')
    .replace(/\/\*.*?\*\//gs, '')
    .replace(/\s+/g, ' ')
    .replace(/,\s*}/g, '}')
    .replace(/,\s*\]/g, ']')
    .replace(/!\./g, '.')
    .replace(/!/g, '');
  
  // Replace references to imported modules with placeholder objects
  // For darkPatterns.find(dp => dp.id === 'dp8')!, we need to replace with just the ID
  // This is complex - for now, we'll keep the structure as is and fix in MongoDB
  
  try {
    const products = eval(`(${arrayStr})`);
    fs.writeFileSync(
      path.join(__dirname, 'data/products.json'),
      JSON.stringify(products, null, 2)
    );
    console.log(`Exported ${products.length} products to products.json`);
    return products;
  } catch (error) {
    console.error('Error parsing products:', error);
    throw error;
  }
}

function exportDarkPatterns() {
  const filePath = path.join(__dirname, '../src/data/mockDarkPatterns.ts');
  let content = fs.readFileSync(filePath, 'utf8');
  
  const start = content.indexOf('export default');
  if (start === -1) return [];
  
  const arrayMatch = content.match(/\[\s*\{[\s\S]*\}\s*\]/);
  if (!arrayMatch) return [];
  
  try {
    const darkPatterns = eval(`(${arrayMatch[0]})`);
    fs.writeFileSync(
      path.join(__dirname, 'data/darkPatterns.json'),
      JSON.stringify(darkPatterns, null, 2)
    );
    console.log(`Exported ${darkPatterns.length} dark patterns to darkPatterns.json`);
    return darkPatterns;
  } catch (error) {
    console.error('Error parsing dark patterns:', error);
    return [];
  }
}

function exportSideEffects() {
  const filePath = path.join(__dirname, '../src/data/mockSideEffects.ts');
  let content = fs.readFileSync(filePath, 'utf8');
  
  const start = content.indexOf('export default');
  if (start === -1) return [];
  
  const arrayMatch = content.match(/\[\s*\{[\s\S]*\}\s*\]/);
  if (!arrayMatch) return [];
  
  try {
    const sideEffects = eval(`(${arrayMatch[0]})`);
    fs.writeFileSync(
      path.join(__dirname, 'data/sideEffects.json'),
      JSON.stringify(sideEffects, null, 2)
    );
    console.log(`Exported ${sideEffects.length} side effects to sideEffects.json`);
    return sideEffects;
  } catch (error) {
    console.error('Error parsing side effects:', error);
    return [];
  }
}

function exportStudies() {
  const filePath = path.join(__dirname, '../src/data/combinedStudies.ts');
  let content = fs.readFileSync(filePath, 'utf8');
  
  const start = content.indexOf('export default');
  if (start === -1) return [];
  
  const arrayMatch = content.match(/\[\s*\{[\s\S]*\}\s*\]/);
  if (!arrayMatch) return [];
  
  try {
    const studies = eval(`(${arrayMatch[0]})`);
    fs.writeFileSync(
      path.join(__dirname, 'data/studies.json'),
      JSON.stringify(studies, null, 2)
    );
    console.log(`Exported ${studies.length} studies to studies.json`);
    return studies;
  } catch (error) {
    console.error('Error parsing studies:', error);
    return [];
  }
}

// Create data directory
fs.mkdirSync(path.join(__dirname, 'data'), { recursive: true });

console.log('Exporting data from TypeScript files...');
exportProducts();
exportDarkPatterns();
exportSideEffects();
exportStudies();
console.log('Data export complete!');