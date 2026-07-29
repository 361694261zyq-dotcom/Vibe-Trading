"""SkillsLoader: loads scenario guides from the skills/ directory.

Uses progressive disclosure:
- System prompt only injects one-line summaries (get_descriptions).
- Full docs loaded on demand (get_content, called by the load_skill tool).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agent.frontmatter import parse_frontmatter as _parse_frontmatter

_SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass
class Skill:
    """Single skill definition.

    Attributes:
        name: Skill name.
        description: Skill description.
        category: Skill category for grouped display.
        body: SKILL.md body text.
        dir_path: Skill directory path (used for on-demand loading of supporting files).
        metadata: Parsed frontmatter metadata.
    """

    name: str
    description: str = ""
    category: str = "other"
    body: str = ""
    dir_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def load_support_file(self, filename: str) -> Optional[str]:
        """Load a supporting file on demand.

        Args:
            filename: File name (e.g. examples.md).

        Returns:
            File content or None.
        """
        if not self.dir_path:
            return None
        path = self.dir_path / filename
        if not path.exists():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None


def _load_skill_dir(dir_path: Path) -> Optional[Skill]:
    """Load a skill from a directory.

    Args:
        dir_path: Skill directory path (must contain SKILL.md).

    Returns:
        Skill instance or None.
    """
    skill_file = dir_path / "SKILL.md"
    if dir_path.is_symlink() or skill_file.is_symlink() or not skill_file.exists():
        return None
    try:
        skill_file.resolve().relative_to(dir_path.resolve())
    except ValueError:
        return None
    try:
        text = skill_file.read_text(encoding="utf-8")
    except Exception:
        return None

    meta, body = _parse_frontmatter(text)
    name = str(meta.get("name", dir_path.name)).strip()
    if not _SKILL_NAME_RE.fullmatch(name):
        return None

    return Skill(
        name=name,
        description=meta.get("description", ""),
        category=meta.get("category", "other"),
        body=body,
        dir_path=dir_path,
        metadata=meta,
    )


USER_SKILLS_DIR = Path.home() / ".vibe-trading" / "skills" / "user"
AGENT_SKILLS_DIR = Path.home() / ".agents" / "skills"


def _render_skill_content(skill: Skill) -> str:
    """Wrap a skill body and qualify its relative support-file links."""
    body = skill.body
    for subdirectory in ("references", "scripts"):
        body = body.replace(f"]({subdirectory}/", f"]({skill.name}/{subdirectory}/")
    return f'<skill name="{skill.name}">\n{body}\n</skill>'


class SkillsLoader:
    """Load skills from bundled skills/ directory and user skills directory.

    Attributes:
        skills: Loaded skill list (bundled + user-created).
    """

    def __init__(
        self,
        skills_dir: Optional[Path] = None,
        user_skills_dir: Optional[Path] = None,
        agent_skills_dir: Optional[Path] = None,
    ) -> None:
        """Initialize SkillsLoader.

        Args:
            skills_dir: Bundled skills directory path; defaults to agent/skills/.
            user_skills_dir: Vibe user skills; defaults to ~/.vibe-trading/skills/user/.
            agent_skills_dir: Shared Agent skills; defaults to ~/.agents/skills/.
        """
        self.skills_dir = skills_dir or Path(__file__).resolve().parents[1] / "skills"
        self._user_skills_dir = user_skills_dir or USER_SKILLS_DIR
        self._agent_skills_dir = agent_skills_dir or AGENT_SKILLS_DIR
        self.skills: List[Skill] = []
        self._load()

    def _load(self) -> None:
        """Load all skill subdirectories from user and bundled directories.

        Vibe user skills override shared Agent skills, which override bundled skills.
        This keeps local patches authoritative while reusing installed official skills.
        """
        seen_names: set[str] = set()
        for directory in (
            self._user_skills_dir,
            self._agent_skills_dir,
            self.skills_dir,
        ):
            if not directory or not directory.exists() or directory.is_symlink():
                continue
            for path in sorted(directory.iterdir()):
                if not path.is_symlink() and path.is_dir() and (path / "SKILL.md").exists():
                    skill = _load_skill_dir(path)
                    if skill and skill.name not in seen_names:
                        self.skills.append(skill)
                        seen_names.add(skill.name)

    # Display order for categories (unlisted categories appear at the end).
    _CATEGORY_ORDER = [
        "data-source", "strategy", "analysis", "asset-class",
        "crypto", "flow", "tool", "other",
    ]

    def get_descriptions(self) -> str:
        """Return skills grouped by category for the system prompt.

        Returns:
            Grouped skill list with category headers.
        """
        if not self.skills:
            return "(no skills)"

        groups: Dict[str, List[Skill]] = {}
        for skill in self.skills:
            groups.setdefault(skill.category, []).append(skill)

        ordered_cats = [c for c in self._CATEGORY_ORDER if c in groups]
        ordered_cats += [c for c in sorted(groups) if c not in ordered_cats]

        lines: List[str] = []
        for cat in ordered_cats:
            lines.append(f"\n### {cat}")
            for skill in groups[cat]:
                lines.append(f"  - {skill.name}: {skill.description}")
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        """Return the full documentation for a skill (used by the load_skill tool).

        Falls back to disk lookup for user skills created mid-session.

        Args:
            name: Skill name.

        Returns:
            XML-wrapped full skill document, or an error message.
        """
        if not _SKILL_NAME_RE.fullmatch(name):
            return f"Error: Invalid skill name '{name}'"

        # Recheck mutable roots first so mid-session installs preserve precedence.
        for directory in (self._user_skills_dir, self._agent_skills_dir):
            if not directory or not directory.exists() or directory.is_symlink():
                continue
            candidate = directory / name
            if candidate.is_symlink():
                continue
            skill = _load_skill_dir(candidate)
            if skill and skill.name == name:
                self.skills = [item for item in self.skills if item.name != name]
                self.skills.append(skill)
                return _render_skill_content(skill)

        for skill in self.skills:
            if skill.name == name:
                return _render_skill_content(skill)

        available = ", ".join(s.name for s in self.skills)
        return f"Error: Unknown skill '{name}'. Available: {available}"
