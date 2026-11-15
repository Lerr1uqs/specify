import hashlib

from specify.contract import ContractIdentity


def test_contract_id_and_title_rules_are_explicit() -> None:
    """确认 Contract 身份来自显式 ID，标题规范化只负责去重。"""

    assert ContractIdentity.is_valid_id("password-login")
    assert not ContractIdentity.is_valid_id("密码登录")
    assert ContractIdentity.normalize_title("  Ａ\u00a0 B\tC  ") == "A B C"


def test_body_hash_normalizes_line_endings_and_outer_blank_lines() -> None:
    """确认正文 hash 只忽略换行风格和边缘空行。"""

    source = "\r\nAlpha\r\n\r\nBeta\r\n"
    expected = hashlib.sha256(b"Alpha\n\nBeta").hexdigest()
    assert ContractIdentity.body_hash(source) == expected
    assert ContractIdentity.body_hash("Alpha\n\nBeta") == expected
    assert ContractIdentity.body_hash("Alpha\nBeta") != expected
