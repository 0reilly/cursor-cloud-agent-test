const fs = require('fs');
const path = require('path');

const studiesPath = path.join(__dirname, 'src/data/mockStudies.ts');
const content = fs.readFileSync(studiesPath, 'utf8');
const lines = content.split('\n');

// Find line where studies array starts
let startLine = -1;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('export const studies: Study[] = [')) {
    startLine = i;
    break;
  }
}
if (startLine === -1) throw new Error('Studies array start not found');

// Find matching closing bracket (simple bracket counting)
let bracketCount = 0;
let endLine = -1;
for (let i = startLine; i < lines.length; i++) {
  const line = lines[i];
  for (let ch of line) {
    if (ch === '[') bracketCount++;
    if (ch === ']') bracketCount--;
    if (bracketCount === 0 && endLine === -1) {
      endLine = i;
      break;
    }
  }
  if (endLine !== -1) break;
}
if (endLine === -1) throw new Error('Matching closing bracket not found');

console.log(`Studies array lines ${startLine} to ${endLine}`);

// Extract existing inner lines (excluding brackets)
const existingInner = lines.slice(startLine + 1, endLine).join('\n');

// Read new studies
const newStudiesPath = path.join(__dirname, 'new_studies.txt');
let newStudies = fs.readFileSync(newStudiesPath, 'utf8').trim();
// Ensure there is a comma after existing inner
let combinedInner = existingInner;
if (!combinedInner.trim().endsWith(',')) {
  combinedInner += ',';
}
combinedInner += '\n' + newStudies;

// Build new array
const newArray = `export const studies: Study[] = [\n${combinedInner}\n];`;

// Replace lines
lines.splice(startLine, endLine - startLine + 1, newArray);

fs.writeFileSync(studiesPath, lines.join('\n'));
console.log('Updated mockStudies.ts with new studies (total: 11 + 19 = 30)');
