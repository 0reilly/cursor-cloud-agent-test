import re
with open('src/data/mockDarkPatterns.ts', 'r', encoding='utf-8') as f:
    content = f.read()
print('Content length:', len(content))
# Try regex
pattern = r"{\s*id: '([^']+)',[\\s\\S]*?name: '([^']+)',[\\s\\S]*?description: '([^']*)',"
matches = re.findall(pattern, content)
print('Matches:', len(matches))
for m in matches:
    print(m[0], m[1])
# Try simpler pattern
pattern2 = r"id: '([^']+)'"
matches2 = re.findall(pattern2, content)
print('All ids:', matches2)