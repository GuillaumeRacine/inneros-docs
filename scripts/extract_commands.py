#!/usr/bin/env python3
"""Extract command/skill definitions from ~/.claude/commands/ and generate catalog pages.

Groups commands by category and generates one MDX page per category.
"""

import re
from pathlib import Path

from sanitizer import sanitize, load_rules

COMMANDS_DIR = Path.home() / ".claude" / "commands"
OUTPUT_DIR = Path(__file__).parent.parent / "app" / "skills-commands" / "catalog"

# Category classification
CATEGORY_MAP = {
    "status": {
        "title": "Status & Monitoring",
        "description": "Commands that report current state across life domains.",
        "keywords": ["-status", "snapshot", "defi-check", "portfolio-"],
    },
    "crypto": {
        "title": "Crypto & DeFi",
        "description": "Commands for delta-neutral trading, yield tracking, and DeFi operations.",
        "keywords": ["dn", "defi-", "portfolio-", "monarch"],
    },
    "writing": {
        "title": "Writing & Publishing",
        "description": "Commands for content creation, publishing pipeline, and archiving.",
        "keywords": ["publish-", "archive-", "tao-", "metrics"],
    },
    "organization": {
        "title": "Organization & Triage",
        "description": "Commands for file organization, inbox management, and cleanup.",
        "keywords": [
            "inbox-", "triage", "organize-", "preview-organize",
            "audit", "save-to-vault", "sync-",
        ],
    },
    "agents": {
        "title": "Agent Spawning",
        "description": "Commands for creating specialized agents with trait combinations.",
        "keywords": ["spawn-"],
    },
    "productivity": {
        "title": "Productivity & Focus",
        "description": "Commands for task management, focus, and ADHD support.",
        "keywords": [
            "todo", "focus", "checkin", "resume", "reset-",
            "weekly-", "capture-", "rec-mode",
        ],
    },
    "home": {
        "title": "Home & Suppliers",
        "description": "Commands for house management, maintenance, and supplier sourcing.",
        "keywords": ["house-", "supplier-", "source-supplier", "travel-"],
    },
    "development": {
        "title": "Development & DevOps",
        "description": "Commands for coding, deployment, testing, and validation.",
        "keywords": [
            "deploy", "ship", "dev-cleanup", "verify-", "new-proto",
            "test-", "read-first", "validate-", "web-check", "screenshot",
            "learning-",
        ],
    },
    "communication": {
        "title": "Communication",
        "description": "Commands for email management, messaging, and notifications.",
        "keywords": ["gmail-", "media-digest", "yasser-"],
    },
}


def classify_command(name: str) -> str:
    """Classify a command into a category."""
    # Status commands are their own category
    if name.endswith("-status"):
        return "status"

    for category, config in CATEGORY_MAP.items():
        if category == "status":
            continue
        for keyword in config.get("keywords", []):
            if keyword in name or name.startswith(keyword):
                return category
    return "development"  # default


def parse_command_file(filepath: Path, rules: dict) -> dict:
    """Parse a command .md file and extract metadata."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    sanitized = sanitize(content, rules)
    lines = sanitized.strip().split("\n")

    name = filepath.stem
    description = ""
    usage = ""

    for i, line in enumerate(lines):
        # Extract description from first non-heading paragraph
        if not description and line.strip() and not line.startswith("#") and not line.startswith("$"):
            description = line.strip()

        # Extract usage pattern
        if re.match(r"^#+\s*usage", line, re.IGNORECASE):
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip().startswith("/") or lines[j].strip().startswith("`/"):
                    usage = lines[j].strip().strip("`")
                    break

    return {
        "name": name,
        "title": name.replace("-", " ").title(),
        "description": description[:200],
        "usage": usage or f"/{name}",
        "line_count": len(lines),
    }


def generate_category_page(category: str, config: dict, commands: list[dict]) -> str:
    """Generate an MDX page for a command category."""
    lines = [
        f"# {config['title']}",
        "",
        config["description"],
        "",
        f"**{len(commands)} commands** in this category.",
        "",
        "| Command | Description |",
        "|---------|-------------|",
    ]

    for cmd in sorted(commands, key=lambda c: c["name"]):
        desc = cmd["description"] or "—"
        lines.append(f"| `/{cmd['name']}` | {desc} |")

    lines.append("")
    lines.append("## Command Details")
    lines.append("")

    for cmd in sorted(commands, key=lambda c: c["name"]):
        lines.append(f"### /{cmd['name']}")
        lines.append("")
        if cmd["description"]:
            lines.append(cmd["description"])
            lines.append("")
        lines.append(f"**Usage:** `{cmd['usage']}`")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def generate_meta(categories: dict) -> str:
    """Generate _meta.js for the catalog directory."""
    entries = []
    for cat in sorted(categories.keys()):
        title = CATEGORY_MAP.get(cat, {}).get("title", cat.title())
        entries.append(f"  '{cat}': '{title}'")

    return "export default {\n" + ",\n".join(entries) + "\n}\n"


def run(output_dir: Path = OUTPUT_DIR):
    """Main extraction and generation."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rules = load_rules()

    if not COMMANDS_DIR.exists():
        print(f"Commands directory not found: {COMMANDS_DIR}")
        return

    commands_by_category: dict[str, list[dict]] = {}
    total = 0

    for filepath in sorted(COMMANDS_DIR.glob("*.md")):
        cmd = parse_command_file(filepath, rules)
        category = classify_command(cmd["name"])

        if category not in commands_by_category:
            commands_by_category[category] = []
        commands_by_category[category].append(cmd)
        total += 1

    print(f"Parsed {total} commands across {len(commands_by_category)} categories")

    for category, commands in commands_by_category.items():
        config = CATEGORY_MAP.get(category, {"title": category.title(), "description": ""})
        content = generate_category_page(category, config, commands)

        page_dir = output_dir / category
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "page.mdx").write_text(content)
        print(f"  Generated {category}/page.mdx ({len(commands)} commands)")

    meta = generate_meta(commands_by_category)
    (output_dir / "_meta.js").write_text(meta)
    print(f"  Generated _meta.js")

    return commands_by_category


if __name__ == "__main__":
    run()
