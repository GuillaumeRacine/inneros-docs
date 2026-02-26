#!/usr/bin/env python3
"""Extract writing pipeline agent definitions and generate stage pages.

Reads from 0_InnerContext/Workflows/Writing/Agents/ and generates
one MDX page per pipeline stage.
"""

import re
from pathlib import Path

from sanitizer import sanitize, load_rules

WRITING_AGENTS_DIR = Path.home() / "Obs_Vault" / "0_InnerContext" / "Workflows" / "Writing" / "Agents"
OUTPUT_DIR = Path(__file__).parent.parent / "app" / "writing-pipeline" / "stages"

STAGE_NAMES = {
    "00": ("Orchestrator", "Editor-in-Chief that manages the full pipeline"),
    "01": ("Researcher", "Gathers sources, data, and raw material"),
    "02": ("Synthesizer", "Extracts patterns and connections from research"),
    "03": ("Narrative Architect", "Designs the story structure and arc"),
    "04": ("Outline Strategist", "Plans sections and content flow"),
    "05": ("Structural Editor", "Optimizes document structure and flow"),
    "06": ("Drafting", "Writes the first complete draft"),
    "07": ("Challenger", "Devil's advocate review for weak arguments"),
    "08": ("Fact Checker", "Verifies claims, data, and sources"),
    "09": ("Style Compression", "Polishes voice and tightens prose"),
    "10": ("Distribution", "Handles publishing and platform formatting"),
    "11": ("Canon Indexer", "Archives and indexes published content"),
    "12": ("Notes Agent", "Captures notes and context during writing"),
}


def parse_writing_agent(filepath: Path, rules: dict) -> dict:
    """Parse a writing agent .md file."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    sanitized = sanitize(content, rules)
    lines = sanitized.strip().split("\n")

    name = filepath.stem
    number = ""
    match = re.match(r"(\d+)_(.+)", name)
    if match:
        number = match.group(1)

    stage_info = STAGE_NAMES.get(number, (name, ""))
    title = stage_info[0]
    default_desc = stage_info[1]

    description = ""
    inputs = []
    outputs = []
    responsibilities = []

    for i, line in enumerate(lines):
        # Extract description
        if not description and line.strip() and not line.startswith("#"):
            description = line.strip()

        # Extract inputs
        if re.match(r"^#+\s*(input|receives|takes)", line, re.IGNORECASE):
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip().startswith("-"):
                    inputs.append(lines[j].strip().lstrip("- "))
                elif lines[j].startswith("#"):
                    break

        # Extract outputs
        if re.match(r"^#+\s*(output|produces|delivers)", line, re.IGNORECASE):
            for j in range(i + 1, min(i + 10, len(lines))):
                if lines[j].strip().startswith("-"):
                    outputs.append(lines[j].strip().lstrip("- "))
                elif lines[j].startswith("#"):
                    break

        # Extract responsibilities
        if re.match(r"^#+\s*(responsibilities|role|does)", line, re.IGNORECASE):
            for j in range(i + 1, min(i + 15, len(lines))):
                if lines[j].strip().startswith("-"):
                    responsibilities.append(lines[j].strip().lstrip("- "))
                elif lines[j].startswith("#"):
                    break

    return {
        "number": number,
        "name": name,
        "title": title,
        "description": description or default_desc,
        "inputs": inputs[:5],
        "outputs": outputs[:5],
        "responsibilities": responsibilities[:10],
    }


def generate_stage_page(agent: dict) -> str:
    """Generate an MDX page for a pipeline stage."""
    lines = [
        f"# Stage {agent['number']}: {agent['title']}",
        "",
        agent["description"],
        "",
    ]

    if agent["responsibilities"]:
        lines.append("## Responsibilities")
        lines.append("")
        for r in agent["responsibilities"]:
            lines.append(f"- {r}")
        lines.append("")

    if agent["inputs"]:
        lines.append("## Inputs")
        lines.append("")
        for inp in agent["inputs"]:
            lines.append(f"- {inp}")
        lines.append("")

    if agent["outputs"]:
        lines.append("## Outputs")
        lines.append("")
        for out in agent["outputs"]:
            lines.append(f"- {out}")
        lines.append("")

    # Add pipeline position context
    num = int(agent["number"]) if agent["number"].isdigit() else -1
    if num > 0:
        prev_num = f"{num - 1:02d}"
        prev_name = STAGE_NAMES.get(prev_num, ("Previous", ""))[0]
        lines.append("## Pipeline Position")
        lines.append("")
        lines.append(f"**Receives from:** Stage {prev_num} ({prev_name})")

    if num >= 0 and num < 12:
        next_num = f"{num + 1:02d}"
        next_name = STAGE_NAMES.get(next_num, ("Next", ""))[0]
        lines.append(f"  ")
        lines.append(f"**Hands off to:** Stage {next_num} ({next_name})")
        lines.append("")

    return "\n".join(lines)


def generate_meta(agents: list[dict]) -> str:
    """Generate _meta.js for stages directory."""
    entries = []
    for agent in sorted(agents, key=lambda a: a["number"]):
        slug = agent["name"].lower().replace("_", "-")
        num = agent["number"]
        title = agent["title"]
        entries.append(f"  '{slug}': 'Stage {num}: {title}'")

    return "export default {\n" + ",\n".join(entries) + "\n}\n"


def run(output_dir: Path = OUTPUT_DIR):
    """Main extraction and generation."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rules = load_rules()

    if not WRITING_AGENTS_DIR.exists():
        print(f"Writing agents directory not found: {WRITING_AGENTS_DIR}")
        return

    agents = []
    for filepath in sorted(WRITING_AGENTS_DIR.glob("*.md")):
        agent = parse_writing_agent(filepath, rules)
        agents.append(agent)

    print(f"Parsed {len(agents)} writing pipeline agents")

    for agent in agents:
        slug = agent["name"].lower().replace("_", "-")
        page_dir = output_dir / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        content = generate_stage_page(agent)
        (page_dir / "page.mdx").write_text(content)
        print(f"  Generated stages/{slug}/page.mdx")

    meta = generate_meta(agents)
    (output_dir / "_meta.js").write_text(meta)
    print("  Generated _meta.js")

    return agents


if __name__ == "__main__":
    run()
