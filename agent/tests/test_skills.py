"""Tests for skill loading, frontmatter parsing, and category grouping."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent.skills import Skill, SkillsLoader, _parse_frontmatter


# ---------------------------------------------------------------------------
# _parse_frontmatter
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_basic(self) -> None:
        text = "---\nname: test-skill\ndescription: A test\n---\nBody here."
        meta, body = _parse_frontmatter(text)
        assert meta["name"] == "test-skill"
        assert meta["description"] == "A test"
        assert body == "Body here."

    def test_category_field(self) -> None:
        text = "---\nname: foo\ncategory: strategy\n---\nContent"
        meta, body = _parse_frontmatter(text)
        assert meta["category"] == "strategy"

    def test_boolean_values(self) -> None:
        text = "---\nname: foo\nactive: true\narchived: false\n---\nBody"
        meta, _ = _parse_frontmatter(text)
        assert meta["active"] is True
        assert meta["archived"] is False

    def test_list_values(self) -> None:
        text = "---\nname: foo\ntags: [a, b, c]\n---\nBody"
        meta, _ = _parse_frontmatter(text)
        assert meta["tags"] == ["a", "b", "c"]

    def test_empty_list(self) -> None:
        text = "---\nname: foo\ntags: []\n---\nBody"
        meta, _ = _parse_frontmatter(text)
        assert meta["tags"] == []

    def test_no_frontmatter(self) -> None:
        text = "Just plain text, no frontmatter."
        meta, body = _parse_frontmatter(text)
        assert meta == {}
        assert body == text.strip()

    def test_multiline_body(self) -> None:
        text = "---\nname: x\n---\nLine 1\nLine 2\nLine 3"
        _, body = _parse_frontmatter(text)
        assert "Line 1" in body
        assert "Line 3" in body

    def test_closing_fence_at_eof_without_trailing_newline(self) -> None:
        # Skill/memory writers often omit the final newline after ---.
        text = "---\nname: eof-skill\ndescription: no trailing newline\n---"
        meta, body = _parse_frontmatter(text)
        assert meta["name"] == "eof-skill"
        assert meta["description"] == "no trailing newline"
        assert body == ""

    def test_empty_frontmatter_block(self) -> None:
        text = "---\n---\nBody only."
        meta, body = _parse_frontmatter(text)
        assert meta == {}
        assert body == "Body only."

    def test_rejects_inline_fence_tail_false_positive(self) -> None:
        # Fence must stand alone on its line; a trailing --- on a value line
        # is not a fence.
        text = "---\nname: foo---"
        meta, body = _parse_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_literal_block_description(self) -> None:
        """Parse a literal-block description from frontmatter."""
        text = (
            "---\n"
            "name: tigeropen\n"
            "description: |\n"
            "  Tiger Brokers OpenAPI Python SDK.\n"
            "  老虎证券 OpenAPI 官方技能。\n"
            "category: tool\n"
            "---\n"
            "Body"
        )

        meta, body = _parse_frontmatter(text)

        assert meta["description"] == (
            "Tiger Brokers OpenAPI Python SDK.\n老虎证券 OpenAPI 官方技能。"
        )
        assert meta["category"] == "tool"
        assert body == "Body"


# ---------------------------------------------------------------------------
# Skill dataclass
# ---------------------------------------------------------------------------


class TestSkill:
    def test_defaults(self) -> None:
        s = Skill(name="test")
        assert s.category == "other"
        assert s.description == ""
        assert s.body == ""
        assert s.metadata == {}

    def test_load_support_file_no_dir(self) -> None:
        s = Skill(name="test")
        assert s.load_support_file("missing.md") is None

    def test_load_support_file(self, tmp_path: Path) -> None:
        (tmp_path / "extra.md").write_text("extra content", encoding="utf-8")
        s = Skill(name="test", dir_path=tmp_path)
        assert s.load_support_file("extra.md") == "extra content"

    def test_load_support_file_missing(self, tmp_path: Path) -> None:
        s = Skill(name="test", dir_path=tmp_path)
        assert s.load_support_file("nope.md") is None


# ---------------------------------------------------------------------------
# SkillsLoader
# ---------------------------------------------------------------------------


class TestSkillsLoader:
    @pytest.fixture()
    def empty_user_dir(self, tmp_path_factory: pytest.TempPathFactory) -> Path:
        """Isolated empty user-skills dir so tests don't pick up real user skills."""
        return tmp_path_factory.mktemp("user_skills_empty")

    @pytest.fixture()
    def empty_agent_dir(self, tmp_path_factory: pytest.TempPathFactory) -> Path:
        """Isolated external Agent-skills dir so tests do not use the real home."""
        return tmp_path_factory.mktemp("agent_skills_empty")

    @pytest.fixture()
    def skills_dir(self, tmp_path: Path) -> Path:
        """Create a minimal skills directory with 3 skills in 2 categories."""
        for name, cat, desc in [
            ("alpha", "strategy", "Alpha strategy"),
            ("beta", "data-source", "Beta source"),
            ("gamma", "strategy", "Gamma strategy"),
        ]:
            d = tmp_path / name
            d.mkdir()
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ncategory: {cat}\ndescription: {desc}\n---\nBody of {name}.",
                encoding="utf-8",
            )
        return tmp_path

    def test_loads_all_skills(self, skills_dir: Path, empty_user_dir: Path, empty_agent_dir: Path) -> None:
        """Load every valid skill from the skills directory."""
        loader = SkillsLoader(
            skills_dir,
            user_skills_dir=empty_user_dir,
            agent_skills_dir=empty_agent_dir,
        )
        assert len(loader.skills) == 3

    def test_category_assignment(self, skills_dir: Path, empty_user_dir: Path, empty_agent_dir: Path) -> None:
        """Assign each loaded skill its declared category."""
        loader = SkillsLoader(
            skills_dir,
            user_skills_dir=empty_user_dir,
            agent_skills_dir=empty_agent_dir,
        )
        cats = {s.name: s.category for s in loader.skills}
        assert cats["alpha"] == "strategy"
        assert cats["beta"] == "data-source"

    def test_get_descriptions_grouped(self, skills_dir: Path, empty_user_dir: Path, empty_agent_dir: Path) -> None:
        """Group skill descriptions in category order."""
        loader = SkillsLoader(
            skills_dir,
            user_skills_dir=empty_user_dir,
            agent_skills_dir=empty_agent_dir,
        )
        desc = loader.get_descriptions()
        # data-source comes before strategy in _CATEGORY_ORDER
        ds_pos = desc.index("data-source")
        st_pos = desc.index("strategy")
        assert ds_pos < st_pos

    def test_get_descriptions_contains_all(self, skills_dir: Path, empty_user_dir: Path, empty_agent_dir: Path) -> None:
        """Include every loaded skill in the descriptions."""
        loader = SkillsLoader(
            skills_dir,
            user_skills_dir=empty_user_dir,
            agent_skills_dir=empty_agent_dir,
        )
        desc = loader.get_descriptions()
        assert "alpha" in desc
        assert "beta" in desc
        assert "gamma" in desc

    def test_get_content_existing(self, skills_dir: Path, empty_user_dir: Path, empty_agent_dir: Path) -> None:
        """Return wrapped content for an existing skill."""
        loader = SkillsLoader(
            skills_dir,
            user_skills_dir=empty_user_dir,
            agent_skills_dir=empty_agent_dir,
        )
        content = loader.get_content("alpha")
        assert '<skill name="alpha">' in content
        assert "Body of alpha" in content

    def test_get_content_missing(self, skills_dir: Path, empty_user_dir: Path, empty_agent_dir: Path) -> None:
        """Return an error for a missing skill."""
        loader = SkillsLoader(
            skills_dir,
            user_skills_dir=empty_user_dir,
            agent_skills_dir=empty_agent_dir,
        )
        content = loader.get_content("nonexistent")
        assert "Error" in content
        assert "nonexistent" in content

    def test_empty_dir(
        self, tmp_path: Path, empty_user_dir: Path, empty_agent_dir: Path
    ) -> None:
        """Handle an empty skills directory."""
        loader = SkillsLoader(
            tmp_path,
            user_skills_dir=empty_user_dir,
            agent_skills_dir=empty_agent_dir,
        )
        assert loader.skills == []
        assert loader.get_descriptions() == "(no skills)"

    def test_dir_without_skill_md_skipped(
        self, tmp_path: Path, empty_user_dir: Path, empty_agent_dir: Path
    ) -> None:
        """Skip skill directories without a SKILL.md file."""
        (tmp_path / "empty_skill").mkdir()
        loader = SkillsLoader(
            tmp_path,
            user_skills_dir=empty_user_dir,
            agent_skills_dir=empty_agent_dir,
        )
        assert len(loader.skills) == 0

    def test_nonexistent_dir(
        self, tmp_path: Path, empty_user_dir: Path, empty_agent_dir: Path
    ) -> None:
        """Handle a nonexistent skills directory."""
        loader = SkillsLoader(
            tmp_path / "nope",
            user_skills_dir=empty_user_dir,
            agent_skills_dir=empty_agent_dir,
        )
        assert loader.skills == []

    def test_loads_external_agent_skill_without_copying(self, tmp_path: Path) -> None:
        """Load an external agent skill directly without copying it."""
        bundled_dir = tmp_path / "bundled"
        user_dir = tmp_path / "vibe-user"
        agent_dir = tmp_path / "agent-skills"
        bundled_dir.mkdir()
        user_dir.mkdir()
        tiger_dir = agent_dir / "tigeropen"
        tiger_dir.mkdir(parents=True)
        (tiger_dir / "SKILL.md").write_text(
            "---\n"
            "name: tigeropen\n"
            "description: |\n"
            "  Tiger Brokers OpenAPI Python SDK.\n"
            "  Official account and market API guidance.\n"
            "---\n"
            "Official Tiger skill body.",
            encoding="utf-8",
        )

        loader = SkillsLoader(
            bundled_dir,
            user_skills_dir=user_dir,
            agent_skills_dir=agent_dir,
        )

        skill = next(skill for skill in loader.skills if skill.name == "tigeropen")
        assert skill.dir_path == tiger_dir
        assert "Tiger Brokers OpenAPI Python SDK" in loader.get_descriptions()
        assert "Official Tiger skill body" in loader.get_content("tigeropen")

        (tiger_dir / "SKILL.md").write_text(
            (tiger_dir / "SKILL.md").read_text(encoding="utf-8")
            + "\n[Trade guide](references/trade.md)",
            encoding="utf-8",
        )
        refreshed = SkillsLoader(
            bundled_dir,
            user_skills_dir=user_dir,
            agent_skills_dir=agent_dir,
        )
        assert "(tigeropen/references/trade.md)" in refreshed.get_content("tigeropen")

    def test_skill_precedence_is_vibe_user_then_agent_then_bundled(self, tmp_path: Path) -> None:
        """Prefer user skills over agent and bundled skills."""
        roots = [tmp_path / name for name in ("bundled", "agent", "user")]
        for root in roots:
            skill_dir = root / "shared"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: shared\n---\nsource={root.name}",
                encoding="utf-8",
            )

        loader = SkillsLoader(
            roots[0],
            user_skills_dir=roots[2],
            agent_skills_dir=roots[1],
        )

        assert "source=user" in loader.get_content("shared")
        assert len([skill for skill in loader.skills if skill.name == "shared"]) == 1

    def test_mid_session_user_skill_overrides_cached_agent_skill(self, tmp_path: Path) -> None:
        """Let a new user skill override a cached agent skill."""
        bundled_dir = tmp_path / "bundled"
        user_dir = tmp_path / "user"
        agent_dir = tmp_path / "agent"
        bundled_dir.mkdir()
        user_dir.mkdir()
        agent_skill = agent_dir / "shared"
        agent_skill.mkdir(parents=True)
        (agent_skill / "SKILL.md").write_text(
            "---\nname: shared\n---\nsource=agent",
            encoding="utf-8",
        )
        loader = SkillsLoader(
            bundled_dir,
            user_skills_dir=user_dir,
            agent_skills_dir=agent_dir,
        )
        assert "source=agent" in loader.get_content("shared")

        user_skill = user_dir / "shared"
        user_skill.mkdir()
        (user_skill / "SKILL.md").write_text(
            "---\nname: shared\n---\nsource=user",
            encoding="utf-8",
        )

        assert "source=user" in loader.get_content("shared")

    @pytest.mark.parametrize("name", ["../outside", "/tmp/outside", "a/b", "."])
    def test_get_content_rejects_unsafe_skill_names(self, tmp_path: Path, name: str) -> None:
        """Reject unsafe skill names when retrieving content."""
        loader = SkillsLoader(
            tmp_path / "bundled",
            user_skills_dir=tmp_path / "user",
            agent_skills_dir=tmp_path / "agent",
        )

        assert loader.get_content(name).startswith("Error: Invalid skill name")

    def test_symlinked_skill_file_is_not_loaded(self, tmp_path: Path) -> None:
        """Do not load a symlinked SKILL.md file."""
        outside = tmp_path / "outside.md"
        outside.write_text("---\nname: linked\n---\nuntrusted", encoding="utf-8")
        agent_dir = tmp_path / "agent"
        skill_dir = agent_dir / "linked"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").symlink_to(outside)

        loader = SkillsLoader(
            tmp_path / "bundled",
            user_skills_dir=tmp_path / "user",
            agent_skills_dir=agent_dir,
        )

        assert "linked" not in {skill.name for skill in loader.skills}

    def test_symlinked_external_skill_is_not_loaded(self, tmp_path: Path) -> None:
        """Do not load a symlinked external skill directory."""
        external = tmp_path / "outside"
        external.mkdir()
        (external / "SKILL.md").write_text(
            "---\nname: outside\n---\nuntrusted",
            encoding="utf-8",
        )
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()
        (agent_dir / "outside").symlink_to(external, target_is_directory=True)

        loader = SkillsLoader(
            tmp_path / "bundled",
            user_skills_dir=tmp_path / "user",
            agent_skills_dir=agent_dir,
        )

        assert "outside" not in {skill.name for skill in loader.skills}
