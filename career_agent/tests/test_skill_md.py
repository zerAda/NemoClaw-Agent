import pytest
import yaml
import os


SKILL_MD_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "skills", "career_agent", "SKILL.md"
)


@pytest.fixture
def skill_data():
    with open(SKILL_MD_PATH, "r") as f:
        return yaml.safe_load(f)


def test_skill_md_is_valid_yaml(skill_data):
    """skills/career_agent/SKILL.md parses as valid YAML."""
    assert skill_data is not None
    assert isinstance(skill_data, dict)


def test_skill_md_has_required_top_level_fields(skill_data):
    """SKILL.md has name, description, and tools fields."""
    assert "name" in skill_data
    assert "description" in skill_data
    assert "tools" in skill_data
    assert isinstance(skill_data["tools"], list)
    assert len(skill_data["tools"]) >= 1


def test_skill_md_has_required_tool_fields(skill_data):
    """Each tool entry has name, description, method, and url fields."""
    required = {"name", "description", "method", "url"}
    for tool in skill_data["tools"]:
        missing = required - set(tool.keys())
        assert not missing, f"Tool '{tool.get('name', '?')}' missing fields: {missing}"


def test_skill_md_urls_point_to_career_agent_service(skill_data):
    """All tool URLs use the career-agent Docker service DNS name."""
    for tool in skill_data["tools"]:
        assert "career-agent:8001" in tool["url"], (
            f"Tool '{tool['name']}' URL must use career-agent:8001, got: {tool['url']}"
        )
