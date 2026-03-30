#!/usr/bin/env python3
"""Extract coaching persona definitions and generate coach + review agent pages.

Reads from 0_InnerContext/Coaching/Coaches/ and generates:
- Individual coach pages in coaching/coaches/
- Review agent pages in coaching/review-agents/
"""

import re
from pathlib import Path

from sanitizer import sanitize, load_rules, escape_mdx

COACHES_DIR = Path.home() / "Obs_Vault" / "0_InnerContext" / "Coaching" / "Coaches"
OUTPUT_COACHES = Path(__file__).parent.parent / "app" / "coaching" / "coaches"
OUTPUT_REVIEWS = Path(__file__).parent.parent / "app" / "coaching" / "review-agents"

# Coach classification
PERSONAL_COACHES = {
    "01": "The Stoic",
    "02": "The Operator",
    "03": "The Father",
    "04": "The Investor",
    "05": "The Creator",
    "06": "The Body",
    "07": "The Shadow",
    "08": "The Executive Coach",
}

REVIEW_AGENTS = {
    "09": "The Weekly Analyst",
    "10": "The Monthly Synthesizer",
    "11": "The Quarterly Strategist",
    "12": "The Annual Reflector",
}

SPECIALIST_COACHES = {
    "13": "The Health Data Analyst",
    "14": "The Orchestrator",
}


def parse_coach_file(filepath: Path, rules: dict) -> dict:
    """Parse a coach .md file and extract key information."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    sanitized = sanitize(content, rules)
    lines = sanitized.strip().split("\n")

    name = filepath.stem
    number = ""
    title = ""
    focus = ""
    when_to_use = ""
    quick_prompts = []

    # Extract number and title from filename
    match = re.match(r"(\d+)_(.+)", name)
    if match:
        number = match.group(1)
        title = match.group(2).replace("_", " ").title()

    for i, line in enumerate(lines):
        # Extract focus area
        if re.match(r"^#+\s*(focus|domain|area)", line, re.IGNORECASE):
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() and not lines[j].startswith("#"):
                    focus = lines[j].strip()
                    break

        # Extract when to use
        if re.match(r"^#+\s*(when to use|trigger|activate)", line, re.IGNORECASE):
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip().startswith("-"):
                    when_to_use += lines[j].strip() + "\n"
                elif lines[j].strip() and not lines[j].startswith("#"):
                    when_to_use += lines[j].strip() + "\n"
                elif lines[j].startswith("#"):
                    break

        # Extract quick prompts
        if re.match(r"^#+\s*(prompts|questions|check.in)", line, re.IGNORECASE):
            for j in range(i + 1, min(i + 15, len(lines))):
                prompt_match = re.match(r'^[-*]\s+"(.+)"', lines[j])
                if prompt_match:
                    quick_prompts.append(prompt_match.group(1))
                elif re.match(r'^[-*]\s+(.+)', lines[j]):
                    quick_prompts.append(re.match(r'^[-*]\s+(.+)', lines[j]).group(1))

    # Fallback: extract first meaningful paragraph as focus
    if not focus:
        for line in lines:
            if line.strip() and not line.startswith("#") and len(line.strip()) > 20:
                focus = line.strip()[:200]
                break

    return {
        "number": number,
        "name": name,
        "title": title,
        "focus": focus,
        "when_to_use": when_to_use.strip(),
        "quick_prompts": quick_prompts[:5],
        "line_count": len(lines),
    }


def generate_coach_page(coach: dict) -> str:
    """Generate an MDX page for a single coach."""
    lines = [
        f"# {coach['title']}",
        "",
    ]

    if coach["focus"]:
        lines.append(coach["focus"])
        lines.append("")

    if coach["when_to_use"]:
        lines.append("## When to Use")
        lines.append("")
        lines.append(coach["when_to_use"])
        lines.append("")

    if coach["quick_prompts"]:
        lines.append("## Quick Prompts")
        lines.append("")
        for prompt in coach["quick_prompts"]:
            lines.append(f'- "{prompt}"')
        lines.append("")

    lines.append("## How to Start a Session")
    lines.append("")
    lines.append("1. Read the coach file to load the persona")
    lines.append('2. Say "I\'m ready. Let\'s go."')
    lines.append("3. Answer questions one at a time")
    lines.append("4. The coach will guide the conversation based on its domain")
    lines.append("")

    return "\n".join(lines)


def generate_meta(items: list[dict], section: str) -> str:
    """Generate _meta.js for a coach/review directory."""
    entries = []
    for item in sorted(items, key=lambda x: x["number"]):
        slug = item["name"].lower().replace("_", "-")
        entries.append(f"  '{slug}': '{item['title']}'")

    return "export default {\n" + ",\n".join(entries) + "\n}\n"


def run():
    """Main extraction and generation."""
    OUTPUT_COACHES.mkdir(parents=True, exist_ok=True)
    OUTPUT_REVIEWS.mkdir(parents=True, exist_ok=True)
    rules = load_rules()

    if not COACHES_DIR.exists():
        print(f"Coaches directory not found: {COACHES_DIR}")
        return

    personal = []
    reviews = []
    specialists = []

    for filepath in sorted(COACHES_DIR.glob("*.md")):
        if filepath.name.startswith("00_"):
            continue  # Skip system overview

        coach = parse_coach_file(filepath, rules)
        number = coach["number"]

        if number in PERSONAL_COACHES:
            personal.append(coach)
        elif number in REVIEW_AGENTS:
            reviews.append(coach)
        elif number in SPECIALIST_COACHES:
            specialists.append(coach)
        else:
            specialists.append(coach)

    print(f"Parsed {len(personal)} personal coaches, {len(reviews)} review agents, {len(specialists)} specialists")

    # Generate personal coach pages
    for coach in personal:
        slug = coach["name"].lower().replace("_", "-")
        page_dir = OUTPUT_COACHES / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        content = escape_mdx(generate_coach_page(coach))
        (page_dir / "page.mdx").write_text(content)
        print(f"  Generated coaches/{slug}/page.mdx")

    # Generate specialist coach pages alongside personal coaches
    for coach in specialists:
        slug = coach["name"].lower().replace("_", "-")
        page_dir = OUTPUT_COACHES / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        content = escape_mdx(generate_coach_page(coach))
        (page_dir / "page.mdx").write_text(content)
        print(f"  Generated coaches/{slug}/page.mdx")

    # Generate review agent pages
    for coach in reviews:
        slug = coach["name"].lower().replace("_", "-")
        page_dir = OUTPUT_REVIEWS / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        content = escape_mdx(generate_coach_page(coach))
        (page_dir / "page.mdx").write_text(content)
        print(f"  Generated review-agents/{slug}/page.mdx")

    # Generate _meta.js files
    all_coaches = personal + specialists
    (OUTPUT_COACHES / "_meta.js").write_text(generate_meta(all_coaches, "coaches"))
    (OUTPUT_REVIEWS / "_meta.js").write_text(generate_meta(reviews, "review-agents"))

    print("  Generated _meta.js files")


if __name__ == "__main__":
    run()
