import pytest


@pytest.mark.skip(reason="Plan 05 creates skills/career_agent/SKILL.md")
def test_skill_md_is_valid_yaml():
    """skills/career_agent/SKILL.md parses as valid YAML"""
    pass


@pytest.mark.skip(reason="Plan 05 creates skills/career_agent/SKILL.md")
def test_skill_md_has_required_tool_fields():
    """Each tool entry has name, description, method, url fields"""
    pass
