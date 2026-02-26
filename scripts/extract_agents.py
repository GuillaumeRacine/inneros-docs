#!/usr/bin/env python3
"""Extract agent definitions from ~/.claude/agents/ and generate catalog pages.

Groups agents by domain and generates one MDX page per domain category.
"""

import re
from pathlib import Path

from sanitizer import sanitize, load_rules

AGENTS_DIR = Path.home() / ".claude" / "agents"
OUTPUT_DIR = Path(__file__).parent.parent / "app" / "agents" / "catalog"

# Domain classification based on agent name prefixes and keywords
DOMAIN_MAP = {
    "trading": {
        "title": "Trading & DeFi",
        "description": "Agents for delta-neutral strategies, position tracking, yield monitoring, and DeFi operations.",
        "prefixes": ["dn-", "hedge-", "trading-", "position-", "lending-", "investment-", "risk-"],
        "keywords": ["trader", "yield", "price", "capital", "reconcil", "tx-"],
    },
    "writing": {
        "title": "Writing & Content",
        "description": "Agents for content creation, publishing, and knowledge management.",
        "keywords": ["tao-", "lyricist", "content-", "podcast-"],
    },
    "music": {
        "title": "Music & Audio",
        "description": "Agents for music production, recording sessions, and audio processing.",
        "keywords": ["ableton", "rc600", "tascam", "audio-", "ghost-league"],
    },
    "home": {
        "title": "Home & Family",
        "description": "Agents for house management, suppliers, and family coordination.",
        "keywords": ["house-", "supplier-", "travel-"],
    },
    "productivity": {
        "title": "Productivity & Tasks",
        "description": "Agents for task management, scheduling, and workflow optimization.",
        "keywords": ["todo-", "calendar-", "workflow-", "session-"],
    },
    "data": {
        "title": "Data & Analysis",
        "description": "Agents for data extraction, analysis, anomaly detection, and reporting.",
        "keywords": [
            "anomaly-", "calibration-", "signal-", "reporting-",
            "insight-", "history-", "hypothesis-",
        ],
    },
    "media": {
        "title": "Media & Files",
        "description": "Agents for file management, photo review, screenshots, and media processing.",
        "keywords": [
            "media-", "photo-", "screenshot-", "image-",
            "dropbox-", "gdrive-", "icloud-", "naming-",
        ],
    },
    "communication": {
        "title": "Communication",
        "description": "Agents for messaging, email, and social platforms.",
        "keywords": ["whatsapp-", "imessage-", "vapi-"],
    },
    "system": {
        "title": "System & Infrastructure",
        "description": "Agents for system architecture, secrets management, documentation, and testing.",
        "keywords": [
            "system-", "secrets-", "doc-", "link-", "vault-",
            "persona-", "recommendations-", "web-animation",
            "learner", "learning-",
            "product-manager",
        ],
    },
}


def classify_agent(name: str) -> str:
    """Classify an agent into a domain based on its name."""
    for domain, config in DOMAIN_MAP.items():
        for prefix in config.get("prefixes", []):
            if name.startswith(prefix):
                return domain
        for keyword in config.get("keywords", []):
            if keyword in name:
                return domain
    return "system"  # default fallback


def parse_agent_file(filepath: Path, rules: dict) -> dict:
    """Parse an agent .md file and extract key metadata."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    sanitized = sanitize(content, rules)
    lines = sanitized.strip().split("\n")

    name = filepath.stem
    title = name.replace("-", " ").title()
    description = ""
    tools = []
    subagent_type = ""

    for i, line in enumerate(lines):
        # Extract first paragraph as description
        if not description and line.strip() and not line.startswith("#"):
            description = line.strip()

        # Look for tools/capabilities
        if re.match(r"^#+\s*(tools|capabilities|available tools)", line, re.IGNORECASE):
            for j in range(i + 1, min(i + 20, len(lines))):
                tool_match = re.match(r"^[-*]\s+\*?\*?(\w+)\*?\*?", lines[j])
                if tool_match:
                    tools.append(tool_match.group(1))

        # Look for subagent_type
        type_match = re.search(r"subagent_type[\"']?\s*[:=]\s*[\"']?(\w+)", line)
        if type_match:
            subagent_type = type_match.group(1)

    return {
        "name": name,
        "title": title,
        "description": description[:200],
        "tools": tools[:10],
        "subagent_type": subagent_type,
        "line_count": len(lines),
    }


def generate_domain_page(domain: str, config: dict, agents: list[dict]) -> str:
    """Generate an MDX page for a domain category."""
    lines = [
        f"# {config['title']}",
        "",
        config["description"],
        "",
        f"**{len(agents)} agents** in this domain.",
        "",
        "| Agent | Description |",
        "|-------|-------------|",
    ]

    for agent in sorted(agents, key=lambda a: a["name"]):
        desc = agent["description"] or "—"
        lines.append(f"| `{agent['name']}` | {desc} |")

    lines.append("")
    lines.append("## Agent Details")
    lines.append("")

    for agent in sorted(agents, key=lambda a: a["name"]):
        lines.append(f"### {agent['title']}")
        lines.append("")
        if agent["description"]:
            lines.append(agent["description"])
            lines.append("")
        if agent["tools"]:
            lines.append(f"**Tools:** {', '.join(agent['tools'])}")
            lines.append("")
        if agent["subagent_type"]:
            lines.append(f"**Type:** `{agent['subagent_type']}`")
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def generate_meta(domains: dict) -> str:
    """Generate _meta.js for the catalog directory."""
    entries = []
    for domain in sorted(domains.keys()):
        title = DOMAIN_MAP[domain]["title"]
        entries.append(f"  '{domain}': '{title}'")

    return "export default {\n" + ",\n".join(entries) + "\n}\n"


def run(output_dir: Path = OUTPUT_DIR):
    """Main extraction and generation."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rules = load_rules()

    if not AGENTS_DIR.exists():
        print(f"Agents directory not found: {AGENTS_DIR}")
        return

    # Parse all agent files
    agents_by_domain: dict[str, list[dict]] = {}
    total = 0

    for filepath in sorted(AGENTS_DIR.glob("*.md")):
        agent = parse_agent_file(filepath, rules)
        domain = classify_agent(agent["name"])

        if domain not in agents_by_domain:
            agents_by_domain[domain] = []
        agents_by_domain[domain].append(agent)
        total += 1

    print(f"Parsed {total} agents across {len(agents_by_domain)} domains")

    # Generate domain pages
    for domain, agents in agents_by_domain.items():
        config = DOMAIN_MAP.get(domain, {"title": domain.title(), "description": ""})
        content = generate_domain_page(domain, config, agents)

        page_dir = output_dir / domain
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "page.mdx").write_text(content)
        print(f"  Generated {domain}/page.mdx ({len(agents)} agents)")

    # Generate _meta.js
    meta = generate_meta(agents_by_domain)
    (output_dir / "_meta.js").write_text(meta)
    print(f"  Generated _meta.js")

    return agents_by_domain


if __name__ == "__main__":
    run()
