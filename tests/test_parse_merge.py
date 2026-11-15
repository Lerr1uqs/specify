import pytest

from specify.errors import SpecifyError
from specify.merge import DeltaMerger
from specify.models import Contract, SpecDocument
from specify.parse.delta import parse_delta
from specify.parse.spec import parse_spec


def test_spec_parser_keeps_nested_markdown_inside_contract_body() -> None:
    """确认代码块、引用、列表和 ### 标题不会切断 Contract 正文。"""

    document = parse_spec(
        "# contract\n\n"
        "## [login] 登录\n\n"
        "基础说明。\n\n"
        "```md\n## [fake-code] 代码标题\n```\n\n"
        "> ## [fake-quote] 引用标题\n\n"
        "- 项目\n\n  ## [fake-list] 列表标题\n\n"
        "### 补充\n\n仍然属于正文。\n\n"
        "## [logout] 登出\n\n退出说明。\n"
    )

    assert [item.id for item in document.contracts] == ["login", "logout"]
    assert "## [fake-code]" in document.contracts[0].body
    assert "## [fake-quote]" in document.contracts[0].body
    assert "## [fake-list]" in document.contracts[0].body
    assert "### 补充" in document.contracts[0].body


def test_spec_parser_rejects_duplicate_ids() -> None:
    """确认一个 spec 内的 Contract ID 必须唯一。"""

    source = (
        "# contract\n\n## [login] 登录\n\n行为。\n\n## [login] 另一登录\n\n行为。\n"
    )
    with pytest.raises(SpecifyError, match="Contract ID 重复"):
        parse_spec(source)


def test_delta_parser_and_merger_use_id_across_rename_and_modify() -> None:
    """确认 RENAMED 和 MODIFIED 始终通过同一个显式 ID 定位。"""

    delta = parse_delta(
        "# delta\n\n"
        "## [RENAMED] [login] 旧标题 -> 新标题\n\n"
        "## [MODIFIED] [login] 新标题\n\n更新后的完整正文。\n"
    )
    spec = SpecDocument([Contract("login", "旧标题", "旧正文。")])
    merged = DeltaMerger().apply(spec, delta)

    assert merged.contracts == [Contract("login", "新标题", "更新后的完整正文。")]
    assert spec.contracts == [Contract("login", "旧标题", "旧正文。")]


def test_delta_parser_requires_removal_reason_and_migration() -> None:
    """确认 REMOVED 必须说明移除原因和替代迁移方式。"""

    with pytest.raises(SpecifyError, match="Reason 和 Migration"):
        parse_delta(
            "# delta\n\n## [REMOVED] [legacy-login] 旧登录\n\n**Reason**: 已淘汰。\n"
        )
