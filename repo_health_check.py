#!/usr/bin/env python3
import os
import re
import ast
import shutil
import subprocess
import sys

# === CONFIG ===
MAX_LINE_LENGTH = 79
UNUSED_IMPORTS_TO_REMOVE = ["asyncio"]
DRY_RUN = False
MAX_FILE_SIZE = 20 * 1024  # 20 KB
BACKUP_DIR = ".health_backup"

# === UTILITIES ===
def should_skip(path):
    return (
        "venv" in path
        or ".venv" in path
        or "/site-packages/" in path
        or "__pycache__" in path
        or not path.endswith(".py")
        or os.path.getsize(path) > MAX_FILE_SIZE
    )


def backup_file(path):
    backup_path = os.path.join(BACKUP_DIR, os.path.relpath(path))
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    shutil.copy2(path, backup_path)


def fix_line_length(path):
    lines = open(path, encoding="utf-8").readlines()
    fixed = []
    changed = False
    for line in lines:
        if len(line.rstrip()) > MAX_LINE_LENGTH:
            split = line.rstrip().rfind(" ", 0, MAX_LINE_LENGTH)
            if split == -1:
                split = MAX_LINE_LENGTH
            fixed.append(line[:split] + "\n")
            fixed.append("    " + line[split:].lstrip() + "\n")
            changed = True
        else:
            fixed.append(line)
    if changed and not DRY_RUN:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(fixed)
        print(f"[FIX] Line length fixed in {path}")


def fix_whitespace_colon(path):
    original = open(path, encoding="utf-8").read()
    fixed = re.sub(r"\s+:", ":", original)
    if fixed != original and not DRY_RUN:
        with open(path, "w", encoding="utf-8") as f:
            f.write(fixed)
        print(f"[FIX] Whitespace before colon in {path}")


def fix_trailing_whitespace(path):
    lines = open(path, encoding="utf-8").readlines()
    fixed = [line.rstrip() + "\n" for line in lines]
    if lines != fixed and not DRY_RUN:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(fixed)
        print(f"[FIX] Trailing whitespace removed in {path}")


def fix_final_newline(path):
    content = open(path, encoding="utf-8").read()
    if not content.endswith("\n") and not DRY_RUN:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n")
        print(f"[FIX] Added final newline to {path}")


def remove_unused_imports(path):
    lines = open(path, encoding="utf-8").readlines()
    new_lines = []
    changed = False
    for line in lines:
        if line.strip().startswith(("import", "from")) and any(
            mod in line for mod in UNUSED_IMPORTS_TO_REMOVE
        ):
            print(f"[FIX] Removed unused import in {path}: {line.strip()}")
            changed = True
            continue
        new_lines.append(line)
    if changed and not DRY_RUN:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)


def remove_debug_statements(path):
    lines = open(path, encoding="utf-8").readlines()
    new_lines = []
    changed = False
    for line in lines:
        if "print(" in line or "logger.debug" in line:
            changed = True
            print(f"[FIX] Removed debug/print in {path}: {line.strip()}")
            continue
        new_lines.append(line)
    if changed and not DRY_RUN:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)


def detect_conflict_markers(path):
    content = open(path, encoding="utf-8").read()
    if any(marker in content for marker in ["<<<<<<<", "=======", ">>>>>>>"]):
        print(f"[ERROR] Merge conflict marker in {path}")
        return True
    return False


def detect_syntax_errors(path):
    try:
        with open(path, encoding="utf-8") as f:
            ast.parse(f.read(), filename=path)
        return False
    except Exception as e:
        print(f"[ERROR] Syntax error in {path}: {e}")
        return True


def run_command(cmd, name):
    try:
        print(f"[RUN] {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print(f"[WARN] {name} not installed, skipping.")
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] {name} failed: {e}")


# === MAIN SCAN ===
def scan_all_py_files():
    bad_count = 0
    py_files = []

    for root, _, files in os.walk("."):
        for f in files:
            full = os.path.join(root, f)
            if should_skip(full):
                continue
            py_files.append(full)

    for path in py_files:
        backup_file(path)
        has_issue = detect_conflict_markers(path) or detect_syntax_errors(path)
        if has_issue:
            bad_count += 1
            continue
        fix_line_length(path)
        fix_whitespace_colon(path)
        fix_trailing_whitespace(path)
        fix_final_newline(path)
        remove_unused_imports(path)
        remove_debug_statements(path)

    if bad_count / max(1, len(py_files)) > 0.25:
        print("[ABORT] Too many broken files. Halting.")
        sys.exit(1)

    run_command(["black", "."], "black")
    run_command(["isort", "."], "isort")
    run_command(["flake8", "."], "flake8")
    run_command(["mypy", "."], "mypy")
    run_command(["bandit", "-r", "."], "bandit")


# === MAIN ===
if __name__ == "__main__":
    os.makedirs(BACKUP_DIR, exist_ok=True)
