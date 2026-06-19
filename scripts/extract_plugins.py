#!/usr/bin/env python3
"""Extract Claude Code PLUGIN definitions from ~/.claude/plugins/cache/.

Plugins ship their own skills, agents, and commands that the native extractors
(extract_agents / extract_commands, which read ~/.claude/{agents,commands}) do NOT
see. This surfaces the whole plugin layer (compound-engineering, ralph-loop,
figma, music plugins, etc.) so the docs reflect true ground truth.

One page per plugin under app/plugins/catalog/<name>/, plus an overview page.
"""
import json
import re
from pathlib import Path

from sanitizer import sanitize, load_rules, escape_mdx

CACHE_DIR = Path.home() / ".claude" / "plugins" / "cache"
OUTPUT_DIR = Path(__file__).parent.parent / "app" / "plugins"
CATALOG_DIR = OUTPUT_DIR / "catalog"


def _version_key(v: str):
    parts = re.findall(r"\d+", v or "")
    return tuple(int(p) for p in parts) if parts else (-1,)


def _frontmatter_desc(md_path: Path, rules: dict) -> str:
    try:
        text = sanitize(md_path.read_text(encoding="utf-8", errors="replace"), rules)
    except Exception:
        return ""
    lines = text.strip().split("\n")
    in_fm = False
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == "---":
            in_fm = True
            continue
        if in_fm:
            if line.strip() == "---":
                break
            m = re.match(r"^description:\s*(.+)", line)
            if m:
                return m.group(1).strip().strip("\"'")[:240]
    # fallback: first meaningful body line
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and s != "---" and len(s) > 10:
            return re.sub(r"^\*?\*?>?\s*", "", s)[:240]
    return ""


def discover_plugins(rules: dict) -> list[dict]:
    """Find plugin roots (latest version each) and collect their skills/agents/commands."""
    if not CACHE_DIR.exists():
        return []
    candidates: dict[str, dict] = {}
    for manifest in CACHE_DIR.rglob(".claude-plugin/plugin.json"):
        root = manifest.parent.parent
        try:
            meta = json.loads(manifest.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        name = meta.get("name") or root.parent.name
        version = meta.get("version", "unknown")
        prev = candidates.get(name)
        if prev and _version_key(prev["version"]) >= _version_key(version):
            continue

        skills = []
        for sk in sorted((root / "skills").glob("*/SKILL.md")) if (root / "skills").exists() else []:
            skills.append({"name": sk.parent.name, "desc": _frontmatter_desc(sk, rules)})
        agents = []
        for ag in sorted((root / "agents").glob("*.md")) if (root / "agents").exists() else []:
            agents.append({"name": ag.stem, "desc": _frontmatter_desc(ag, rules)})
        commands = []
        for cm in sorted((root / "commands").glob("*.md")) if (root / "commands").exists() else []:
            commands.append({"name": cm.stem, "desc": _frontmatter_desc(cm, rules)})

        candidates[name] = {
            "name": name,
            "version": version,
            "description": sanitize(meta.get("description", ""), rules)[:300],
            "author": (meta.get("author") or {}).get("name", "") if isinstance(meta.get("author"), dict) else str(meta.get("author", "")),
            "repository": meta.get("repository", ""),
            "license": meta.get("license", ""),
            "skills": skills,
            "agents": agents,
            "commands": commands,
        }
    return sorted(candidates.values(), key=lambda p: p["name"])


def _table(rows: list[dict], head: str) -> list[str]:
    out = [f"| {head} | Description |", "|------|-------------|"]
    for r in rows:
        out.append(f"| `{r['name']}` | {r['desc'] or '—'} |")
    return out


def plugin_page(p: dict) -> str:
    L = [f"# {p['name']}", ""]
    if p["description"]:
        L += [p["description"], ""]
    meta_bits = []
    if p["version"] and p["version"] != "unknown":
        meta_bits.append(f"**Version:** {p['version']}")
    if p["author"]:
        meta_bits.append(f"**Author:** {p['author']}")
    if p["license"]:
        meta_bits.append(f"**License:** {p['license']}")
    if p["repository"]:
        repo = p["repository"] if isinstance(p["repository"], str) else p["repository"].get("url", "")
        if repo:
            meta_bits.append(f"**Repo:** {repo}")
    if meta_bits:
        L += [" · ".join(meta_bits), ""]
    L += [f"Provides **{len(p['skills'])} skills**, **{len(p['agents'])} agents**, "
          f"**{len(p['commands'])} commands**.", ""]
    if p["skills"]:
        L += ["## Skills", ""] + _table(p["skills"], "Skill") + [""]
    if p["agents"]:
        L += ["## Agents", ""] + _table(p["agents"], "Agent") + [""]
    if p["commands"]:
        L += ["## Commands", ""] + _table(p["commands"], "Command") + [""]
    return "\n".join(L)


def registered_uncached() -> list[str]:
    """Plugins listed in installed_plugins.json whose cache is empty/missing."""
    import os
    f = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    out = []
    try:
        d = json.loads(f.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return out
    for key, insts in (d.get("plugins") or {}).items():
        cached = False
        for inst in insts:
            p = inst.get("installPath", "")
            if p and os.path.isdir(p) and os.listdir(p):
                cached = True
        if not cached:
            out.append(key.split("@")[0])
    return sorted(set(out))


def overview_page(plugins: list[dict]) -> str:
    tot_s = sum(len(p["skills"]) for p in plugins)
    tot_a = sum(len(p["agents"]) for p in plugins)
    tot_c = sum(len(p["commands"]) for p in plugins)
    L = [
        "# Plugins",
        "",
        "Claude Code **plugins** bundle their own skills, agents, and commands on top "
        "of the native `~/.claude/{agents,commands}` layer. They are installed from "
        "marketplaces into `~/.claude/plugins/` and are a first-class part of the "
        "agent-tech ground truth — most notably **compound-engineering**, the default "
        "coding loop.",
        "",
        f"**{len(plugins)} plugins** installed, contributing **{tot_s} skills**, "
        f"**{tot_a} agents**, and **{tot_c} commands**.",
        "",
        "| Plugin | Skills | Agents | Commands | Description |",
        "|--------|:------:|:------:|:--------:|-------------|",
    ]
    for p in plugins:
        L.append(f"| [`{p['name']}`](/plugins/catalog/{p['name']}) | {len(p['skills'])} "
                 f"| {len(p['agents'])} | {len(p['commands'])} | {p['description'] or '—'} |")
    uncached = registered_uncached()
    if uncached:
        L += ["", "## Registered but not cached", "",
              "These plugins are registered in `installed_plugins.json` but their cache "
              "is empty (not materialized on this machine), so their skills/agents are "
              "not currently active:", "",
              ", ".join(f"`{n}`" for n in uncached) + ".", ""]
    L += ["", "> These come from Claude Code's plugin system and are **separate** from "
          "the native agents/commands and from the **Codex** environment — see "
          "[Environments](/environments) for the cross-tool map.", ""]
    return "\n".join(L)


def run(output_dir: Path = OUTPUT_DIR):
    rules = load_rules()
    plugins = discover_plugins(rules)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Discovered {len(plugins)} plugins")
    for p in plugins:
        pdir = CATALOG_DIR / p["name"]
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "page.mdx").write_text(escape_mdx(plugin_page(p)))
        print(f"  {p['name']}: {len(p['skills'])} skills, {len(p['agents'])} agents, {len(p['commands'])} commands")

    (output_dir / "page.mdx").write_text(escape_mdx(overview_page(plugins)))
    # catalog _meta.js (ordered by name)
    meta = "export default {\n" + ",\n".join(
        f"  '{p['name']}': '{p['name']}'" for p in plugins) + "\n}\n"
    (CATALOG_DIR / "_meta.js").write_text(meta)
    # section _meta.js
    (output_dir / "_meta.js").write_text(
        "export default {\n  index: 'Overview',\n  catalog: 'Plugin Catalog'\n}\n")
    print("  Generated plugins overview + _meta.js")
    return plugins


if __name__ == "__main__":
    run()
