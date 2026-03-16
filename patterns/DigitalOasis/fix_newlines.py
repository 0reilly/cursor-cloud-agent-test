#!/usr/bin/env python3
import os
import sys

def fix_file(filepath):
    with open(filepath, 'rb') as f:
        content = f.read()
    # Detect if file contains literal backslash-n sequences
    if b'\\n' in content:
        print(f'Fixing {filepath}')
        # Replace \n with newline
        content = content.replace(b'\\n', b'\n')
        # Replace \\" with \" ? Let's also fix escaped quotes
        # content = content.replace(b'\\\"', b'\"')
        with open(filepath, 'wb') as f:
            f.write(content)
        return True
    return False

def main():
    root = 'src'
    fixed = 0
    for dirpath, dirnames, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith('.ts') or filename.endswith('.tsx'):
                filepath = os.path.join(dirpath, filename)
                if fix_file(filepath):
                    fixed += 1
    # Also check App.tsx
    if os.path.exists('App.tsx'):
        if fix_file('App.tsx'):
            fixed += 1
    print(f'Fixed {fixed} files')

if __name__ == '__main__':
    main()