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
    "scripts": Path.home() / "Obs_Vault" / "_System" / "Claude_Code" / "Scripts",
    "hooks": Path.home() / ".claude" / "hooks",
    "skills": Path.home() / "Obs_Vault" / "_System" / "Claude_Code" / "Skills",
    "workflows": Path.home() / "Obs_Vault" / "0_InnerContext" / "Workflows",
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


def get_stats() -> dict:
    """Collect all system statistics."""
    stats = {}

    stats["agents"] = count_files(PATHS["agents"])
    stats["commands"] = count_files(PATHS["commands"])
    stats["coaches"] = count_files(PATHS["coaches"]) - 1  # Exclude overview file
    stats["writing_stages"] = count_files(PATHS["writing_agents"])
    stats["scripts"] = count_py_scripts(PATHS["scripts"])
    stats["hooks"] = count_files(PATHS["hooks"]) if PATHS["hooks"].exists() else 0

    # Count workflow files recursively
    if PATHS["workflows"].exists():
        stats["workflows"] = len(list(PATHS["workflows"].rglob("*.md")))
    else:
        stats["workflows"] = 0

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
        f"| Python Scripts | {stats['scripts']} |",
        f"| Hooks | {stats['hooks']} |",
        f"| Workflow Files | {stats['workflows']} |",
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
        f"| Automation Layer | Scripts + Hooks | Scheduled processing |",
        "",
        "## Domain Coverage",
        "",
        "| Domain | Agents | Commands | Total |",
        "|--------|--------|----------|-------|",
    ]

    # Domain breakdown (approximations based on known counts)
    domains = [
        ("Trading & DeFi", "18+", "6", "24+"),
        ("Writing & Content", "2", "5", "7"),
        ("Music & Audio", "5", "2", "7"),
        ("Home & Family", "3", "8", "11"),
        ("Productivity", "5", "10", "15"),
        ("Data & Analysis", "7", "3", "10"),
        ("Media & Files", "8", "5", "13"),
        ("Communication", "3", "4", "7"),
        ("System & Infrastructure", "10+", "15+", "25+"),
    ]

    for name, agents, commands, total in domains:
        lines.append(f"| {name} | {agents} | {commands} | {total} |")

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
