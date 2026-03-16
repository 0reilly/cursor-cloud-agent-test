#!/usr/bin/env python3
import re

with open('src/screens/ProductDetailScreen.tsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line with exampleText
for i, line in enumerate(lines):
    if 'exampleText' in line and '{dp.description}' in line:
        # Insert after this line
        indent = len(line) - len(line.lstrip())
        new_lines = []
        new_lines.append(' ' * indent + '{dp.verification && (\n')
        new_lines.append(' ' * (indent + 2) + '<View style={styles.verificationBadge}>\n')
        new_lines.append(' ' * (indent + 4) + '<Ionicons name="shield-checkmark" size={14} color="#10b981" />\n')
        new_lines.append(' ' * (indent + 4) + '<Text style={styles.verificationText}>Legally verified</Text>\n')
        new_lines.append(' ' * (indent + 2) + '</View>\n')
        new_lines.append(' ' * indent + ')}\n')
        # Insert after line i
        lines[i+1:i+1] = new_lines
        break

# Add styles before the final closing bracket
# Find the line with '});' at the end
for i, line in enumerate(lines):
    if line.strip() == '});':
        # Insert before this line
        lines.insert(i, '  verificationBadge: {\n')
        lines.insert(i+1, '    flexDirection: \'row\',\n')
        lines.insert(i+2, '    alignItems: \'center\',\n')
        lines.insert(i+3, '    backgroundColor: \'#f0fdf4\',\n')
        lines.insert(i+4, '    paddingHorizontal: 10,\n')
        lines.insert(i+5, '    paddingVertical: 6,\n')
        lines.insert(i+6, '    borderRadius: 12,\n')
        lines.insert(i+7, '    alignSelf: \'flex-start\',\n')
        lines.insert(i+8, '    marginTop: 10,\n')
        lines.insert(i+9, '  },\n')
        lines.insert(i+10, '  verificationText: {\n')
        lines.insert(i+11, '    fontSize: 12,\n')
        lines.insert(i+12, '    color: \'#065f46\',\n')
        lines.insert(i+13, '    fontWeight: \'600\',\n')
        lines.insert(i+14, '    marginLeft: 6,\n')
        lines.insert(i+15, '  },\n')
        break

with open('src/screens/ProductDetailScreen.tsx', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Added verification badge UI and styles.')