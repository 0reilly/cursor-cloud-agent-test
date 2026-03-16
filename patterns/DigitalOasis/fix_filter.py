import re
import sys

with open('filter_verified.py', 'r') as f:
    content = f.read()

# Replace the problematic line
pattern = r'    desc_escaped = description\\.replace\\(.*?\\)'
new_line = '    desc_escaped = description.replace(\"\\'\", \"\\\\\\\\\\'\")'
content = re.sub(pattern, new_line, content, flags=re.MULTILINE)

with open('filter_verified.py', 'w') as f:
    f.write(content)
print('Fixed')