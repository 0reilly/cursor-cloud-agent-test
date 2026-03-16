import re

with open('final_filter.py', 'r') as f:
    content = f.read()

# Fix the regex line
pattern = r'dp_match = re\.search\(r\\\"dp\\\\.id\\\\s*===\\\\s*\'\(\[\^\'\]\+\)\'\\\", entry\)'
replacement = '    dp_match = re.search(r\"dp\\\\.id\\\\s*===\\\\s*\'([^\']+)\'\", entry)'
content = re.sub(pattern, replacement, content)

with open('final_filter.py', 'w') as f:
    f.write(content)
print('Fixed regex line')