#!/usr/bin/env python3
"""PII sanitizer for InnerOS documentation generation.

Reads sanitize_rules.json and applies path replacements, regex patterns,
and name blocklist to any text content before it's written as documentation.
"""

import json
import re
import sys
from pathlib import Path

RULES_PATH = Path(__file__).parent.parent / "config" / "sanitize_rules.json"


def load_rules(rules_path: Path = RULES_PATH) -> dict:
    with open(rules_path) as f:
        return json.load(f)


def sanitize(text: str, rules: dict | None = None) -> str:
    """Apply all sanitization rules to text."""
    if rules is None:
        rules = load_rules()

    # 1. Path replacements (longest first to avoid partial matches)
    path_items = sorted(
        rules["path_replacements"].items(),
        key=lambda x: len(x[0]),
        reverse=True,
    )
    for original, replacement in path_items:
        text = text.replace(original, replacement)

    # 2. Name blocklist (case-insensitive, standalone words only)
    # Use negative lookbehind/ahead for hyphens to avoid matching inside
    # hyphenated identifiers like "yasser-report"
    for name in rules["name_blocklist"]:
        pattern = re.compile(
            rf"(?<![-/\w])\b{re.escape(name)}\b(?![-/\w])",
            re.IGNORECASE,
        )
        text = pattern.sub(rules["name_replacement"], text)

    # 3. Regex patterns
    for rule in rules["regex_patterns"]:
        text = re.sub(rule["pattern"], rule["replacement"], text)

    # 4. Escape MDX-breaking HTML-like patterns
    text = escape_mdx(text)

    return text


def escape_mdx(text: str) -> str:
    """Escape HTML-like patterns that break MDX parsing.

    Catches:
    - Bare <tag> outside code blocks/backticks (e.g. <id>, <3KB)
    - Angle brackets used as less-than in prose
    """
    lines = text.split("\n")
    result = []
    in_code_block = False

    for line in lines:
        # Track fenced code blocks
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block:
            result.append(line)
            continue

        # Outside code blocks: escape bare < that aren't in inline code
        # Split by inline code spans to preserve them
        parts = re.split(r"(`[^`]+`)", line)
        escaped_parts = []
        for part in parts:
            if part.startswith("`") and part.endswith("`"):
                escaped_parts.append(part)
            else:
                # Replace < followed by a word char or digit (looks like a tag)
                part = re.sub(r"<(\w)", r"&lt;\1", part)
                escaped_parts.append(part)
        result.append("".join(escaped_parts))

    return "\n".join(result)


def sanitize_file(filepath: Path, rules: dict | None = None) -> str:
    """Read and sanitize a file."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    return sanitize(content, rules)


def check_leaks(text: str, rules: dict | None = None) -> list[str]:
    """Check for any remaining PII leaks after sanitization."""
    if rules is None:
        rules = load_rules()

    leaks = []
    for name in rules["name_blocklist"]:
        if re.search(rf"(?<![-/\w])\b{re.escape(name)}\b(?![-/\w])", text, re.IGNORECASE):
            leaks.append(f"Name found: {name}")

    for rule in rules["regex_patterns"]:
        matches = re.findall(rule["pattern"], text)
        if matches:
            leaks.append(f"{rule['description']}: {len(matches)} match(es)")

    for original in rules["path_replacements"]:
        if original in text:
            leaks.append(f"Raw path found: {original}")

    return leaks


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: sanitizer.py <file_or_text> [--check]")
        sys.exit(1)

    target = sys.argv[1]
    check_mode = "--check" in sys.argv

    path = Path(target)
    if path.exists():
        content = sanitize_file(path)
    else:
        content = sanitize(target)

    if check_mode:
        leaks = check_leaks(content)
        if leaks:
            print("PII leaks detected:")
            for leak in leaks:
                print(f"  - {leak}")
            sys.exit(1)
        else:
            print("No PII leaks detected.")
    else:
        print(content)
