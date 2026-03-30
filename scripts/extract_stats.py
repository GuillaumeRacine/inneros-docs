#!/usr/bin/env python3
"""Extract system statistics and generate a stats page.

Counts agents, commands, coaches, writing stages, workflows, scripts,
hooks, and NightCrew stages to produce a comprehensive stats page.
"""

from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "app" / "reference" / "system-stats"

PATHS = {
    "agents": Path.home() / ".claude" / "agents",
    "commands": Path.home() / ".claude" / "commands",
    "coaches": Path.home() / "Obs_Vault" / "0_InnerContext" / "Coaching" / "Coaches",
    "writing_agents": Path.home() / "Obs_Vault" / "0_InnerContext" / "Workflows" / "Writing" / "Agents",
    "vault_scripts": Path.home() / "Obs_Vault" / "_System" / "Claude_Code" / "Scripts",
    "automation_scripts": Path.home() / "Context" / "scripts",
    "hooks": Path.home() / ".claude" / "hooks",
    "settings": Path.home() / ".claude" / "settings.json",
    "skills": Path.home() / "Obs_Vault" / "_System" / "Claude_Code" / "Skills",
    "workflows": Path.home() / "Obs_Vault" / "0_InnerContext" / "Workflows",
    "areas": Path.home() / "Obs_Vault" / "2_Areas",
    "rules": Path.home() / ".claude" / "rules",
}


def count_files(path: Path, pattern: str = "*.md") -> int:
    """Count matching files in a directory."""
    if not path.exists():
        return 0
    return len(list(path.glob(pattern)))


def count_py_scripts(path: Path) -> int:
    """Count Python scripts."""
    if not path.exists():
        return 0
    return len(list(path.glob("*.py")))


def count_hooks() -> int:
    """Count hooks from settings.json."""
    import json
    settings = PATHS["settings"]
    if not settings.exists():
        return 0
    try:
        data = json.loads(settings.read_text())
        hooks = data.get("hooks", {})
        return sum(len(v) for v in hooks.values() if isinstance(v, list))
    except Exception:
        return 0


def get_stats() -> dict:
    """Collect all system statistics."""
    stats = {}

    stats["agents"] = count_files(PATHS["agents"])
    stats["commands"] = count_files(PATHS["commands"])
    stats["coaches"] = count_files(PATHS["coaches"]) - 1  # Exclude overview file
    stats["writing_stages"] = count_files(PATHS["writing_agents"])
    stats["vault_scripts"] = count_py_scripts(PATHS["vault_scripts"])
    stats["automation_scripts"] = count_py_scripts(PATHS["automation_scripts"])
    stats["scripts"] = stats["vault_scripts"] + stats["automation_scripts"]
    stats["hooks"] = count_hooks()
    stats["rules"] = count_files(PATHS["rules"])

    # Count workflow files recursively
    if PATHS["workflows"].exists():
        stats["workflows"] = len(list(PATHS["workflows"].rglob("*.md")))
    else:
        stats["workflows"] = 0

    # Count areas
    if PATHS["areas"].exists():
        stats["areas"] = len([d for d in PATHS["areas"].iterdir() if d.is_dir()])
    else:
        stats["areas"] = 0

    # Count skill packs
    if PATHS["skills"].exists():
        stats["skill_packs"] = len([d for d in PATHS["skills"].iterdir() if d.is_dir()])
    else:
        stats["skill_packs"] = 0

    stats["total"] = (
        stats["agents"] + stats["commands"] + stats["coaches"]
        + stats["writing_stages"] + stats["scripts"]
    )
    stats["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    return stats


def get_domain_counts() -> dict[str, int]:
    """Get actual agent counts per domain by running classification."""
    try:
        from extract_agents import classify_agent, AGENTS_DIR
        counts: dict[str, int] = {}
        if AGENTS_DIR.exists():
            for f in AGENTS_DIR.glob("*.md"):
                domain = classify_agent(f.stem)
                counts[domain] = counts.get(domain, 0) + 1
        return counts
    except Exception:
        return {}


def generate_stats_page(stats: dict) -> str:
    """Generate the system stats MDX page."""
    lines = [
        "# System Statistics",
        "",
        f"*Auto-generated on {stats['generated_at']}*",
        "",
        "## Component Counts",
        "",
        "| Component | Count |",
        "|-----------|-------|",
        f"| Agents | {stats['agents']} |",
        f"| Commands/Skills | {stats['commands']} |",
        f"| Coaching Personas | {stats['coaches']} |",
        f"| Writing Pipeline Stages | {stats['writing_stages']} |",
        f"| Automation Scripts | {stats['scripts']} ({stats['vault_scripts']} vault + {stats['automation_scripts']} pipeline) |",
        f"| Hooks | {stats['hooks']} |",
        f"| Rules | {stats['rules']} |",
        f"| Workflow Files | {stats['workflows']} |",
        f"| Life Areas | {stats['areas']} |",
        f"| Skill Packs | {stats['skill_packs']} |",
        f"| **Total Automations** | **{stats['total']}** |",
        "",
        "## Architecture Layers",
        "",
        "| Layer | Components | Purpose |",
        "|-------|-----------|---------|",
        f"| Agent Layer | {stats['agents']} agents | Autonomous task execution |",
        f"| Command Layer | {stats['commands']} commands | User-invoked procedures |",
        f"| Coaching Layer | {stats['coaches']} personas | Personal development |",
        f"| Writing Layer | {stats['writing_stages']} stages | Content creation pipeline |",
        f"| Automation Layer | {stats['scripts']} scripts + {stats['hooks']} hooks | Scheduled processing |",
        f"| Knowledge Layer | {stats['areas']} areas + {stats['workflows']} workflows | Life domain management |",
        "",
        "## Domain Coverage",
        "",
        "| Domain | Agents |",
        "|--------|--------|",
    ]

    domain_counts = get_domain_counts()
    for domain in sorted(domain_counts.keys(), key=lambda d: domain_counts[d], reverse=True):
        lines.append(f"| {domain.replace('-', ' ').title()} | {domain_counts[domain]} |")

    if not domain_counts:
        lines.append("| *Run agent extraction first* | — |")

    lines.append("")

    return "\n".join(lines)


def run(output_dir: Path = OUTPUT_DIR):
    """Main stats generation."""
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = get_stats()
    content = generate_stats_page(stats)

    (output_dir / "page.mdx").write_text(content)
    print(f"Generated system-stats/page.mdx")
    print(f"  Agents: {stats['agents']}")
    print(f"  Commands: {stats['commands']}")
    print(f"  Coaches: {stats['coaches']}")
    print(f"  Writing stages: {stats['writing_stages']}")
    print(f"  Scripts: {stats['scripts']}")
    print(f"  Total: {stats['total']}")

    return stats


if __name__ == "__main__":
    run()
