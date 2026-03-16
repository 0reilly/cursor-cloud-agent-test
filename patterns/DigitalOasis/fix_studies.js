const fs = require('fs');
const path = require('path');

const studiesPath = path.join(__dirname, 'src/data/mockStudies.ts');
let lines = fs.readFileSync(studiesPath, 'utf8').split('\n');

// Find first line containing '];'
let closingBracketLine = -1;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].trim() === '];') {
    closingBracketLine = i;
    break;
  }
}
if (closingBracketLine === -1) {
  throw new Error('Could not find closing bracket');
}
console.log(`Closing bracket at line ${closingBracketLine}`);

// Find line containing 'export default studies;'
let exportDefaultLine = -1;
for (let i = closingBracketLine + 1; i < lines.length; i++) {
  if (lines[i].includes('export default studies;')) {
    exportDefaultLine = i;
    break;
  }
}
if (exportDefaultLine === -1) {
  // maybe default export is missing; we'll add it
  lines = lines.slice(0, closingBracketLine + 1);
  lines.push('', 'export default studies;');
} else {
  // keep lines up to export default line
  lines = lines.slice(0, exportDefaultLine + 1);
}

fs.writeFileSync(studiesPath, lines.join('\n'));
console.log('Fixed studies file');
