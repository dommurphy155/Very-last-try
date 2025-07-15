#!/usr/bin/env python3
import os
import re
import subprocess
import sys

MAX_LINE_LENGTH = 79
UNUSED_IMPORTS_TO_REMOVE = [
    'asyncio',
]

def fix_line_length(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    changed = False

    for line in lines:
        if len(line.rstrip('\n')) > MAX_LINE_LENGTH:
            # Naive wrap: split on last space before MAX_LINE_LENGTH
            line_content = line.rstrip('\n')
            split_pos = line_content.rfind(' ', 0, MAX_LINE_LENGTH)
            if split_pos == -1:
                split_pos = MAX_LINE_LENGTH
            first_part = line_content[:split_pos]
            second_part = line_content[split_pos:].lstrip()
            fixed_lines.append(first_part + '\n')
            fixed_lines.append('    ' + second_part + '\n')  # indent continuation line 4 spaces
            changed = True
        else:
            fixed_lines.append(line)
    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(fixed_lines)
        print(f'[FIX] Fixed line length in {path}')

def remove_unused_imports(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    changed = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from '):
            if any(mod in stripped for mod in UNUSED_IMPORTS_TO_REMOVE):
                print(f'[FIX] Removed unused import in {path}: {stripped}')
                changed = True
                continue
        new_lines.append(line)
    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

def fix_whitespace_colon(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    fixed_content = re.sub(r'\s+:', ':', content)
    if fixed_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f'[FIX] Fixed whitespace before colon in {path}')

def run_command(cmd, exit_on_fail=True):
    print(f'[RUN] {" ".join(cmd)}')
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        if exit_on_fail:
            print(f'[ERROR] Command failed: {" ".join(cmd)}')
            sys.exit(result.returncode)
    return result

def scan_and_fix_pyfiles(root='.'):
    py_files = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(dirpath, f))
    for filepath in py_files:
        fix_line_length(filepath)
        remove_unused_imports(filepath)
        fix_whitespace_colon(filepath)

def main():
    scan_and_fix_pyfiles()

    try:
        run_command(['black', '.'])
    except FileNotFoundError:
        print('[WARN] black not installed, skipping.')

    try:
        run_command(['isort', '.'])
    except FileNotFoundError:
        print('[WARN] isort not installed, skipping.')

    flake8 = run_command(['flake8', '.'], exit_on_fail=False)
    print(flake8.stdout)
    print(flake8.stderr)

    sys.exit(flake8.returncode)

if __name__ == '__main__':
    main()