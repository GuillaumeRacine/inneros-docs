#!/usr/bin/env python3
"""Orchestrator for InnerOS documentation generation.

Routes to individual extractors, manages section generation,
and reports on changes. Used by NightCrew Stage 15 and /docs-refresh.

Usage:
    python generate_docs.py                     # Generate all sections
    python generate_docs.py --section agents    # Generate specific section
    python generate_docs.py --section commands coaches
    python generate_docs.py --check             # PII leak check only
    python generate_docs.py --stats             # Show current stats
"""

import argparse
import sys
import time
from pathlib import Path

# Add scripts dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sanitizer import load_rules, check_leaks

PROJECT_ROOT = Path(__file__).parent.parent
APP_DIR = PROJECT_ROOT / "app"

SECTIONS = {
    "agents": {
        "description": "Agent catalog pages (9 domain categories)",
        "module": "extract_agents",
    },
    "commands": {
        "description": "Command catalog pages (8 categories)",
        "module": "extract_commands",
    },
    "coaches": {
        "description": "Coaching persona + review agent pages",
        "module": "extract_coaches",
    },
    "writing": {
        "description": "Writing pipeline stage pages (13 stages)",
        "module": "extract_writing_pipeline",
    },
    "stats": {
        "description": "System statistics page",
        "module": "extract_stats",
    },
}


def run_section(name: str) -> bool:
    """Run a single section's extractor."""
    if name not in SECTIONS:
        print(f"Unknown section: {name}")
        print(f"Available: {', '.join(SECTIONS.keys())}")
        return False

    section = SECTIONS[name]
    print(f"\n{'='*60}")
    print(f"Generating: {name} - {section['description']}")
    print(f"{'='*60}")

    try:
        module = __import__(section["module"])
        module.run()
        return True
    except Exception as e:
        print(f"ERROR generating {name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all() -> dict:
    """Run all section extractors."""
    results = {}
    start = time.time()

    for name in SECTIONS:
        results[name] = run_section(name)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"Generation complete in {elapsed:.1f}s")
    print(f"{'='*60}")

    for name, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {name}: {status}")

    return results


def check_pii() -> bool:
    """Check all generated MDX files for PII leaks."""
    rules = load_rules()
    all_clean = True

    generated_dirs = [
        APP_DIR / "agents" / "catalog",
        APP_DIR / "skills-commands" / "catalog",
        APP_DIR / "coaching" / "coaches",
        APP_DIR / "coaching" / "review-agents",
        APP_DIR / "writing-pipeline" / "stages",
        APP_DIR / "reference" / "system-stats",
        APP_DIR / "data-sources" / "connected",
    ]

    for gen_dir in generated_dirs:
        if not gen_dir.exists():
            continue
        for mdx_file in gen_dir.rglob("*.mdx"):
            content = mdx_file.read_text(encoding="utf-8", errors="replace")
            leaks = check_leaks(content, rules)
            if leaks:
                all_clean = False
                print(f"PII leak in {mdx_file.relative_to(PROJECT_ROOT)}:")
                for leak in leaks:
                    print(f"  - {leak}")

    if all_clean:
        print("No PII leaks detected in generated content.")

    return all_clean


def show_stats():
    """Show current stats without regenerating."""
    try:
        from extract_stats import get_stats
        stats = get_stats()
        print("Current InnerOS Statistics:")
        for key, value in stats.items():
            if key != "generated_at":
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error getting stats: {e}")


def main():
    parser = argparse.ArgumentParser(description="InnerOS documentation generator")
    parser.add_argument(
        "--section",
        nargs="+",
        choices=list(SECTIONS.keys()),
        help="Generate specific section(s)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for PII leaks in generated content",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show current system stats",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available sections",
    )

    args = parser.parse_args()

    if args.list:
        print("Available sections:")
        for name, config in SECTIONS.items():
            print(f"  {name}: {config['description']}")
        return

    if args.stats:
        show_stats()
        return

    if args.check:
        clean = check_pii()
        sys.exit(0 if clean else 1)

    if args.section:
        results = {}
        for section in args.section:
            results[section] = run_section(section)
        failed = [s for s, ok in results.items() if not ok]
        if failed:
            print(f"\nFailed sections: {', '.join(failed)}")
            sys.exit(1)
    else:
        results = run_all()
        failed = [s for s, ok in results.items() if not ok]
        if failed:
            sys.exit(1)

    # Always check PII after generation
    print("\nRunning PII check...")
    check_pii()


if __name__ == "__main__":
    main()
