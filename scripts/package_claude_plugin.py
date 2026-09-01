#!/usr/bin/env python3
"""Package ADRs, the arc42 template, and the Reference Architectures into
Claude plugin skills.

Implements Path 2 of DS-273's fan-out sync (Git -> Claude plugin) for the full
scope DS-278 commits to at project close-out: not just ADRs, but the arc42/C4
template and all Tier-1 Reference Architectures too. Git remains the single
source of truth; this script only ever reads from the repo's convention docs
and writes claude-plugin/skills/**, so it can be re-run any number of times
without drifting from Git.

Real decision records only for adr-lookup: adr/NNNN-*.md with NNNN >= 0001.
adr/0000-adr-template.md is a reserved number for the blank template, and the
two process docs (adr-template-lifecycle.md, adr-governance-model.md) are
about the ADR process itself, not decisions — both are excluded from that
skill (they're convention docs, published to Confluence like any other).
"""

import hashlib
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = ROOT / "adr"
ARC42_TEMPLATE = ROOT / "documentation-template" / "arc42-c4-template.md"
RA_DIR = ROOT / "reference-architectures"
PLUGIN_DIR = ROOT / "claude-plugin" / "skills"
SKILL_DIR = PLUGIN_DIR / "adr-lookup"

ADR_FILENAME_RE = re.compile(r"^(\d{4})-.+\.md$")


def find_adrs() -> list[Path]:
    def is_real_adr(p: Path) -> bool:
        m = ADR_FILENAME_RE.match(p.name)
        return bool(m) and int(m.group(1)) >= 1

    return sorted(p for p in ADR_DIR.glob("*.md") if is_real_adr(p))


def extract_title_and_status(text: str) -> tuple[str, str]:
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    status_match = re.search(r"^##\s+Status\s*\n(.+)$", text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Untitled ADR"
    status = status_match.group(1).strip() if status_match else "unknown"
    return title, status


def content_hash(adrs: list[Path]) -> str:
    h = hashlib.sha256()
    for path in adrs:
        h.update(path.read_bytes())
    return h.hexdigest()[:12]


def build_skill(adrs: list[Path]) -> None:
    adrs_out = SKILL_DIR / "adrs"
    if adrs_out.exists():
        shutil.rmtree(adrs_out)
    adrs_out.mkdir(parents=True)

    index_lines = [
        "# ADR Lookup — Accepted Architecture Decisions",
        "",
        "Synced from `adr/*.md` in the architecture-convention repo. Do not edit these files "
        "directly here — edit the source ADR and re-run `scripts/package_claude_plugin.py`.",
        "",
        "| ADR | Title | Status |",
        "|---|---|---|",
    ]

    for adr_path in adrs:
        text = adr_path.read_text(encoding="utf-8")
        title, status = extract_title_and_status(text)
        shutil.copy(adr_path, adrs_out / adr_path.name)
        index_lines.append(f"| [{adr_path.stem}](adrs/{adr_path.name}) | {title} | {status} |")

    version = f"{len(adrs)}.{content_hash(adrs)}"
    index_lines += ["", f"_Skill version: `{version}`_"]

    skill_md = SKILL_DIR / "SKILL.md"
    skill_md.write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    version_file = SKILL_DIR / "VERSION"
    version_file.write_text(version + "\n", encoding="utf-8")

    print(f"Packaged {len(adrs)} ADR(s) into {SKILL_DIR.relative_to(ROOT)} (version {version})")


def build_arc42_template_skill() -> None:
    skill_dir = PLUGIN_DIR / "arc42-template"
    skill_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(ARC42_TEMPLATE, skill_dir / "arc42-c4-template.md")
    version = content_hash([ARC42_TEMPLATE])
    (skill_dir / "SKILL.md").write_text(
        "# arc42/C4 Template — for scaffolding new project architecture docs\n\n"
        "Synced from `documentation-template/arc42-c4-template.md`. Use this as the starting "
        "structure when asked to draft or review a project's architecture documentation.\n\n"
        f"See [arc42-c4-template.md](arc42-c4-template.md).\n\n_Skill version: `1.{version}`_\n",
        encoding="utf-8",
    )
    (skill_dir / "VERSION").write_text(f"1.{version}\n", encoding="utf-8")
    print(f"Packaged arc42 template into {skill_dir.relative_to(ROOT)} (version 1.{version})")


def build_reference_architectures_skill() -> list[Path]:
    ras = sorted(RA_DIR.glob("*.md"))
    skill_dir = PLUGIN_DIR / "reference-architectures"
    ras_out = skill_dir / "ras"
    if ras_out.exists():
        shutil.rmtree(ras_out)
    ras_out.mkdir(parents=True)

    index_lines = [
        "# Reference Architectures — Tier 1 Blueprints",
        "",
        "Synced from `reference-architectures/*.md`. Cite the specific RA (and the ADRs it "
        "links to) when giving architectural guidance instead of a generic answer.",
        "",
        "| Reference Architecture |",
        "|---|",
    ]
    for ra_path in ras:
        shutil.copy(ra_path, ras_out / ra_path.name)
        title_match = re.search(r"^#\s+(.+)$", ra_path.read_text(encoding="utf-8"), re.MULTILINE)
        title = title_match.group(1).strip() if title_match else ra_path.stem
        index_lines.append(f"| [{title}](ras/{ra_path.name}) |")

    version = content_hash(ras)
    index_lines += ["", f"_Skill version: `{len(ras)}.{version}`_"]
    (skill_dir / "SKILL.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    (skill_dir / "VERSION").write_text(f"{len(ras)}.{version}\n", encoding="utf-8")
    print(f"Packaged {len(ras)} RA(s) into {skill_dir.relative_to(ROOT)} (version {len(ras)}.{version})")
    return ras


def main() -> int:
    adrs = find_adrs()
    if not adrs:
        print("No ADRs found under adr/ matching NNNN-*.md — nothing to package.", file=sys.stderr)
        return 1
    build_skill(adrs)

    if not ARC42_TEMPLATE.exists():
        print(f"WARNING: {ARC42_TEMPLATE} not found — skipping arc42-template skill.", file=sys.stderr)
    else:
        build_arc42_template_skill()

    ras = build_reference_architectures_skill()
    if not ras:
        print("WARNING: no reference architectures found under reference-architectures/.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
