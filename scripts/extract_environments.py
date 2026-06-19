#!/usr/bin/env python3
"""Generate the ENVIRONMENTS section: a clear map of what lives in Claude Code
vs Codex, so the docs make explicit which agent-tech is available in each tool.

Reads live from ~/.claude (native + plugins) and ~/.codex (config, skills,
commands, AGENTS.md, MCP). Writes:
  app/environments/page.mdx            -- side-by-side overview
  app/environments/claude-code/page.mdx
  app/environments/codex/page.mdx
"""
import json
import re
from pathlib import Path

try:
    import tomllib
except Exception:
    tomllib = None

from sanitizer import sanitize, load_rules, escape_mdx
from extract_plugins import discover_plugins

OUTPUT_DIR = Path(__file__).parent.parent / "app" / "environments"
CLAUDE = Path.home() / ".claude"
CODEX = Path.home() / ".codex"


def _count(glob_root: Path, pattern: str) -> int:
    return len(list(glob_root.glob(pattern))) if glob_root.exists() else 0


def claude_inventory(rules: dict) -> dict:
    plugins = discover_plugins(rules)
    return {
        "agents": _count(CLAUDE / "agents", "*.md"),
        "commands": _count(CLAUDE / "commands", "*.md"),
        "rules": _count(CLAUDE / "rules", "*.md"),
        "hooks": _count(CLAUDE / "hooks", "*"),
        "context": _count(CLAUDE / "context", "*.md"),
        "resolver": (CLAUDE / "resolver.md").exists(),
        "plugins": len(plugins),
        "plugin_skills": sum(len(p["skills"]) for p in plugins),
        "plugin_agents": sum(len(p["agents"]) for p in plugins),
        "plugin_names": [p["name"] for p in plugins],
        "mcp": _claude_mcp(),
    }


def _claude_mcp() -> list[str]:
    names = set()
    for f in [Path.home() / ".mcp.json", Path.home() / ".claude.json"]:
        try:
            d = json.loads(f.read_text(encoding="utf-8", errors="replace"))
            names.update((d.get("mcpServers") or {}).keys())
        except Exception:
            pass
    return sorted(names)


def codex_inventory(rules: dict) -> dict:
    inv = {"model": "", "reasoning": "", "service_tier": "", "mcp": [],
           "skills": [], "commands": [], "agents_md": (CODEX / "AGENTS.md").exists(),
           "trusted_projects": 0, "memories": (CODEX / "memories").exists(),
           "goals": any(CODEX.glob("goals_*.sqlite"))}
    cfg = CODEX / "config.toml"
    if cfg.exists() and tomllib:
        try:
            data = tomllib.loads(cfg.read_text(encoding="utf-8", errors="replace"))
            inv["model"] = str(data.get("model", ""))
            inv["reasoning"] = str(data.get("model_reasoning_effort", ""))
            inv["service_tier"] = str(data.get("service_tier", ""))
            inv["mcp"] = sorted((data.get("mcp_servers") or {}).keys())
            inv["trusted_projects"] = len(data.get("projects") or {})
        except Exception:
            pass
    sk_dir = CODEX / "skills"
    if sk_dir.exists():
        for s in sorted(sk_dir.glob("*/SKILL.md")):
            inv["skills"].append({"name": s.parent.name, "desc": _fm_desc(s, rules)})
    cm_dir = CODEX / "commands"
    if cm_dir.exists():
        for c in sorted(cm_dir.glob("*.md")):
            inv["commands"].append({"name": c.stem, "desc": _fm_desc(c, rules)})
    return inv


def _fm_desc(p: Path, rules: dict) -> str:
    try:
        text = sanitize(p.read_text(encoding="utf-8", errors="replace"), rules)
    except Exception:
        return ""
    in_fm = False
    for i, line in enumerate(text.split("\n")):
        if i == 0 and line.strip() == "---":
            in_fm = True; continue
        if in_fm:
            if line.strip() == "---":
                break
            m = re.match(r"^description:\s*(.+)", line)
            if m:
                return m.group(1).strip().strip("\"'")[:200]
    for line in text.split("\n"):
        s = line.strip()
        if s and not s.startswith("#") and s != "---" and len(s) > 10:
            return re.sub(r"^\*?\*?>?\s*", "", s)[:200]
    return ""


def overview(c: dict, x: dict) -> str:
    L = [
        "# Environments: Claude Code + Codex",
        "",
        "This system runs across **two AI coding environments**. They share the same "
        "machine, secrets, and many projects, but each has its **own** agent/skill "
        "inventory and config. This page is the cross-tool map so it's always clear "
        "*what is available where*.",
        "",
        "| Capability | Claude Code | Codex |",
        "|------------|-------------|-------|",
        f"| Native agents | **{c['agents']}** (`~/.claude/agents`) | — (uses `AGENTS.md` instructions) |",
        f"| Native commands / skills | **{c['commands']}** (`~/.claude/commands`) | **{len(x['commands'])}** (`~/.codex/commands`) |",
        f"| Skill packs | via plugins (below) | **{len(x['skills'])}** (`~/.codex/skills`) |",
        f"| Plugins | **{c['plugins']}** → {c['plugin_skills']} skills + {c['plugin_agents']} agents | — |",
        f"| Rules (path-scoped) | **{c['rules']}** (`~/.claude/rules`) | — |",
        f"| Hooks | **{c['hooks']}** (`~/.claude/hooks`) | — |",
        f"| Resolver / on-demand context | **{c['context']}** files{' + resolver.md' if c['resolver'] else ''} | — |",
        f"| Instruction layer | `CLAUDE.md` (global + project) | `AGENTS.md` ({'present' if x['agents_md'] else 'none'}) |",
        f"| Default model | (session) | **{x['model'] or '—'}** (reasoning: {x['reasoning'] or '—'}) |",
        f"| MCP servers | {', '.join(f'`{m}`' for m in c['mcp']) or '—'} | {', '.join(f'`{m}`' for m in x['mcp']) or '—'} |",
        f"| Persistent memory | auto-memory + `/memory-search` | sqlite memories{' + goals' if x['goals'] else ''} |",
        "",
        "## At a glance",
        "",
        f"- **Claude Code** is the primary environment: {c['agents']} agents, "
        f"{c['commands']} commands, {c['plugins']} plugins "
        f"({c['plugin_skills']} plugin skills + {c['plugin_agents']} plugin agents), "
        f"{c['rules']} rules, {c['hooks']} hooks, and a resolver/context layer. "
        "See [Claude Code](/environments/claude-code).",
        f"- **Codex** is the secondary environment (OpenAI): model `{x['model']}`, "
        f"{len(x['skills'])} skill packs, {len(x['commands'])} commands, an `AGENTS.md` "
        "instruction layer, and its own MCP + memory. See [Codex](/environments/codex).",
        "- Cross-model review bridges the two: `/cross-review` has Claude implement and "
        "**Codex** independently grade the diff (PASS/FAIL).",
        "",
        "> The [Agents](/agents), [Skills & Commands](/skills-commands), and "
        "[Plugins](/plugins) catalogs document the Claude Code side in depth; the "
        "[Codex](/environments/codex) page documents the Codex side.",
    ]
    return "\n".join(L)


def claude_page(c: dict) -> str:
    L = [
        "# Claude Code Environment",
        "",
        "The primary environment. Everything is plain files under `~/.claude/` "
        "(plus vault-synced mirrors).",
        "",
        "## Inventory",
        "",
        "| Layer | Count | Location |",
        "|-------|------:|----------|",
        f"| Agents | {c['agents']} | `~/.claude/agents/` |",
        f"| Commands / skills | {c['commands']} | `~/.claude/commands/` |",
        f"| Plugins | {c['plugins']} | `~/.claude/plugins/` |",
        f"| — plugin skills | {c['plugin_skills']} | (bundled) |",
        f"| — plugin agents | {c['plugin_agents']} | (bundled) |",
        f"| Rules (path-scoped) | {c['rules']} | `~/.claude/rules/` |",
        f"| Hooks | {c['hooks']} | `~/.claude/hooks/` |",
        f"| On-demand context | {c['context']} | `~/.claude/context/` |",
        "",
        f"**MCP servers:** {', '.join(f'`{m}`' for m in c['mcp']) or '—'}",
        "",
        "**Resolver:** `~/.claude/resolver.md` maps task triggers → on-demand "
        "`context/*.md` files, keeping the always-on `CLAUDE.md` lean.",
        "",
        "**Installed plugins:** " + (", ".join(f"`{n}`" for n in c["plugin_names"]) or "—") + ".",
        "",
        "See [Plugins](/plugins) for the full per-plugin catalog.",
    ]
    return "\n".join(L)


def codex_page(x: dict) -> str:
    L = [
        "# Codex Environment",
        "",
        "The secondary environment (OpenAI Codex CLI). Config in `~/.codex/`.",
        "",
        "## Configuration",
        "",
        "| Setting | Value |",
        "|---------|-------|",
        f"| Model | `{x['model'] or '—'}` |",
        f"| Reasoning effort | `{x['reasoning'] or '—'}` |",
        f"| Service tier | `{x['service_tier'] or '—'}` |",
        f"| Trusted projects | {x['trusted_projects']} |",
        f"| Instruction layer | `AGENTS.md` ({'present' if x['agents_md'] else 'none'}) |",
        f"| MCP servers | {', '.join(f'`{m}`' for m in x['mcp']) or '—'} |",
        f"| Memory | sqlite memories{' + goals tracking' if x['goals'] else ''} |",
        "",
    ]
    if x["skills"]:
        L += [f"## Skill packs ({len(x['skills'])})", "",
              "| Skill | Description |", "|-------|-------------|"]
        for s in x["skills"]:
            L.append(f"| `{s['name']}` | {s['desc'] or '—'} |")
        L.append("")
    if x["commands"]:
        L += [f"## Commands ({len(x['commands'])})", "",
              "| Command | Description |", "|---------|-------------|"]
        for c in x["commands"]:
            L.append(f"| `{c['name']}` | {c['desc'] or '—'} |")
        L.append("")
    L += ["> Codex shares the machine, secrets, and many trusted projects with "
          "Claude Code, but maintains its own skills, commands, MCP, and memory. "
          "See [Environments](/environments) for the cross-tool comparison."]
    return "\n".join(L)


def run(output_dir: Path = OUTPUT_DIR):
    rules = load_rules()
    c = claude_inventory(rules)
    x = codex_inventory(rules)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "page.mdx").write_text(escape_mdx(overview(c, x)))
    for sub, content in [("claude-code", claude_page(c)), ("codex", codex_page(x))]:
        d = output_dir / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / "page.mdx").write_text(escape_mdx(content))
    (output_dir / "_meta.js").write_text(
        "export default {\n  index: 'Overview',\n  'claude-code': 'Claude Code',\n  codex: 'Codex'\n}\n")
    print(f"  Claude Code: {c['agents']} agents, {c['commands']} commands, {c['plugins']} plugins")
    print(f"  Codex: model {x['model']}, {len(x['skills'])} skills, {len(x['commands'])} commands")
    return {"claude": c, "codex": x}


if __name__ == "__main__":
    run()
