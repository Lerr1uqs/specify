import json
from pathlib import Path

from click.testing import CliRunner, Result

from specify.cli import main


def invoke(runner: CliRunner, root: Path, *args: str) -> Result:
    """在隔离项目目录中调用真实 CLI 命令树。"""

    return runner.invoke(main, ["--root", str(root), *args])


def initialize(runner: CliRunner, root: Path) -> None:
    """建立测试项目，并确认 init action 成功。"""

    result = runner.invoke(main, ["init", str(root)])
    assert result.exit_code == 0, result.output


def write_spec(
    root: Path, spec_type: str, spec_id: str, contract_id: str, title: str, body: str
) -> Path:
    """写入符合当前协议的最小正式 spec。"""

    target = root / "spec" / "specs" / spec_type / spec_id / "spec.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f"# contract\n\n## [{contract_id}] {title}\n\n{body}\n", encoding="utf-8"
    )
    return target


def complete_tasks(change_dir: Path) -> None:
    """将脚手架中的任务标记为完成，供实现状态迁移使用。"""

    path = change_dir / "tasks.md"
    path.write_text(
        "# tasks\n\n## 1. 工作\n\n- [x] 1.1 完成并复核变更。\n", encoding="utf-8"
    )


def test_init_preserves_customized_templates(tmp_path: Path) -> None:
    """重复初始化保留作者修改过的模板文档。"""

    runner = CliRunner()
    initialize(runner, tmp_path)
    template = tmp_path / "spec/template/capability.md"
    template.write_text("# 我们项目自己的能力模板\n", encoding="utf-8")

    result = runner.invoke(main, ["init", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert template.read_text(encoding="utf-8") == "# 我们项目自己的能力模板\n"


def test_create_rejects_missing_configured_template(tmp_path: Path) -> None:
    """模板引用损坏时不创建半成品 spec 目录。"""

    runner = CliRunner()
    initialize(runner, tmp_path)
    config = tmp_path / "spec/config.yaml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "template/requirement.md", "template/missing.md"
        ),
        encoding="utf-8",
    )

    result = invoke(runner, tmp_path, "create", "requirement", "payment-policy")

    assert result.exit_code == 1
    assert "模板不存在" in result.output
    assert not (tmp_path / "spec/specs/requirement/payment-policy").exists()


def test_cli_actions_and_no_impact_lifecycle(tmp_path: Path) -> None:
    """覆盖 init/create/index/show/list 和无 spec 影响 change 的完整生命周期。"""

    runner = CliRunner()
    initialize(runner, tmp_path)
    assert (tmp_path / "spec/template/requirement.md").is_file()
    assert (tmp_path / "spec/template/capability.md").is_file()
    assert (tmp_path / "spec/template/feature.md").is_file()
    assert (tmp_path / "spec/template/architecture.md").is_file()
    assert (tmp_path / "spec/template/component.md").is_file()

    result = invoke(runner, tmp_path, "create", "capability", "auth")
    assert result.exit_code == 0, result.output
    spec_path = tmp_path / "spec/specs/capability/auth/spec.md"
    assert (
        spec_path.read_bytes()
        == (tmp_path / "spec/template/capability.md").read_bytes()
    )
    spec_path.write_text(
        "# contract\n\n## [login] 登录\n\n用户可以登录。\n", encoding="utf-8"
    )

    assert invoke(runner, tmp_path, "validate", "--specs").exit_code == 0
    result = invoke(runner, tmp_path, "create", "architecture", "service-map")
    assert result.exit_code == 0, result.output
    architecture_spec = tmp_path / "spec/specs/architecture/service-map/spec.md"
    assert (
        architecture_spec.read_bytes()
        == (tmp_path / "spec/template/architecture.md").read_bytes()
    )
    architecture_spec.write_text(
        "# contract\n\n## [service-map] Service map\n\nSystem tree.\n",
        encoding="utf-8",
    )
    assert invoke(runner, tmp_path, "validate", "--specs").exit_code == 0
    assert invoke(runner, tmp_path, "index", "build").exit_code == 0
    assert "capability:auth" in invoke(runner, tmp_path, "list").output
    shown = invoke(runner, tmp_path, "--json", "show", "capability:auth")
    assert shown.exit_code == 0
    assert json.loads(shown.output)["contracts"][0]["id"] == "login"
    assert invoke(runner, tmp_path, "show", "invalid-reference").exit_code == 2
    assert invoke(runner, tmp_path, "show", "capability:missing").exit_code == 3

    result = invoke(
        runner, tmp_path, "change", "create", "bugfix", "fix-internal-cache"
    )
    assert result.exit_code == 0, result.output
    change_dir = tmp_path / "spec/changes/proposed/bugfix/fix-internal-cache"
    assert (change_dir / "change.md").is_file()
    assert not (change_dir / "proposal.md").exists()
    assert not (change_dir / "design.md").exists()
    assert (
        invoke(runner, tmp_path, "change", "baseline", "fix-internal-cache").exit_code
        == 1
    )
    assert (
        invoke(runner, tmp_path, "change", "status", "fix-internal-cache").exit_code
        == 0
    )
    assert (
        invoke(runner, tmp_path, "change", "verify", "fix-internal-cache").exit_code
        == 0
    )
    # tasks 尚未全部完成时，proposed change 不能进入 implemented。
    assert (
        invoke(runner, tmp_path, "change", "implement", "fix-internal-cache").exit_code
        == 1
    )

    complete_tasks(change_dir)
    assert (
        invoke(runner, tmp_path, "change", "implement", "fix-internal-cache").exit_code
        == 0
    )
    assert (
        invoke(runner, tmp_path, "change", "implement", "fix-internal-cache").exit_code
        == 1
    )
    assert (
        invoke(
            runner,
            tmp_path,
            "change",
            "reject",
            "fix-internal-cache",
            "--reason",
            "不应迁移",
        ).exit_code
        == 1
    )
    assert (
        invoke(
            runner, tmp_path, "change", "remove", "fix-internal-cache", "--yes"
        ).exit_code
        == 1
    )
    assert (
        invoke(
            runner,
            tmp_path,
            "change",
            "reject",
            "fix-internal-cache",
            "--reason",
            "已进入 implemented",
        ).exit_code
        == 1
    )
    assert (
        invoke(runner, tmp_path, "change", "sync", "fix-internal-cache").exit_code == 0
    )
    assert (
        invoke(runner, tmp_path, "change", "archive", "fix-internal-cache").exit_code
        == 0
    )
    assert invoke(runner, tmp_path, "validate").exit_code == 0
    assert invoke(runner, tmp_path, "validate", "--changes").exit_code == 0
    assert invoke(runner, tmp_path, "validate", "--specs").exit_code == 0
    assert invoke(runner, tmp_path, "validate", "--archived").exit_code == 0
    assert (
        invoke(runner, tmp_path, "change", "status", "fix-internal-cache").exit_code
        == 0
    )
    assert (
        invoke(runner, tmp_path, "change", "implement", "fix-internal-cache").exit_code
        == 1
    )
    assert (
        invoke(
            runner,
            tmp_path,
            "change",
            "reject",
            "fix-internal-cache",
            "--reason",
            "不应迁移",
        ).exit_code
        == 1
    )
    assert (
        invoke(
            runner, tmp_path, "change", "remove", "fix-internal-cache", "--yes"
        ).exit_code
        == 1
    )
    assert (
        invoke(runner, tmp_path, "change", "sync", "fix-internal-cache").exit_code == 1
    )
    assert (
        invoke(runner, tmp_path, "change", "archive", "fix-internal-cache").exit_code
        == 1
    )

    json_validation = invoke(runner, tmp_path, "--json", "validate", "--specs")
    assert json_validation.exit_code == 0
    assert json.loads(json_validation.output)["ok"] is True

    archived_context = next(
        (tmp_path / "spec/changes/archived").glob("bugfix/*/change.md")
    )
    archived_context.write_text("有人修改了归档内容。\n", encoding="utf-8")
    assert invoke(runner, tmp_path, "validate", "--archived").exit_code == 1


def test_sync_conflict_rejects_every_target_before_writing(tmp_path: Path) -> None:
    """验证多目标中任一基线冲突时，所有 spec 和 sync receipt 都保持原样。"""

    runner = CliRunner()
    initialize(runner, tmp_path)
    first = write_spec(
        tmp_path, "capability", "login", "login", "登录", "用户可以登录。"
    )
    second = write_spec(
        tmp_path,
        "component",
        "auth-service",
        "credential-check",
        "凭据校验",
        "服务校验密码。",
    )

    result = invoke(
        runner,
        tmp_path,
        "change",
        "create",
        "feat",
        "add-passkey",
        "--affect",
        "capability:login:modify",
        "--affect",
        "component:auth-service:modify",
    )
    assert result.exit_code == 0, result.output
    change_dir = tmp_path / "spec/changes/proposed/feat/add-passkey"
    (change_dir / "deltas/capability/login.md").write_text(
        "# delta\n\n## [MODIFIED] [login] 登录\n\n用户可用密码或通行密钥登录。\n",
        encoding="utf-8",
    )
    (change_dir / "deltas/component/auth-service.md").write_text(
        "# delta\n\n## [MODIFIED] [credential-check] 凭据校验\n\n服务校验密码与通行密钥断言。\n",
        encoding="utf-8",
    )
    assert invoke(runner, tmp_path, "change", "baseline", "add-passkey").exit_code == 0
    assert invoke(runner, tmp_path, "change", "verify", "add-passkey").exit_code == 0
    complete_tasks(change_dir)
    assert invoke(runner, tmp_path, "change", "implement", "add-passkey").exit_code == 0
    change_dir = tmp_path / "spec/changes/implemented/feat/add-passkey"

    # 模拟另一个 change 先更新第二份 spec，迫使本次 sync 检出过期基线。
    second.write_text(
        "# contract\n\n## [credential-check] 凭据校验\n\n服务校验密码、通行密钥和硬件令牌。\n",
        encoding="utf-8",
    )
    first_before = first.read_bytes()
    second_before = second.read_bytes()
    index_before = (tmp_path / "spec/spec-index.md").read_bytes()
    metadata_before = (change_dir / "meta-data.yaml").read_bytes()

    result = invoke(runner, tmp_path, "change", "sync", "add-passkey")
    assert result.exit_code == 1
    assert "基线已变化" in result.output
    assert first.read_bytes() == first_before
    assert second.read_bytes() == second_before
    assert (tmp_path / "spec/spec-index.md").read_bytes() == index_before
    assert (change_dir / "meta-data.yaml").read_bytes() == metadata_before

    # 作者先把最新 Contract 语义纳入 delta，再显式刷新基线并重试。
    (change_dir / "deltas/component/auth-service.md").write_text(
        "# delta\n\n## [MODIFIED] [credential-check] 凭据校验\n\n服务校验密码、通行密钥断言和硬件令牌。\n",
        encoding="utf-8",
    )
    assert invoke(runner, tmp_path, "change", "baseline", "add-passkey").exit_code == 0
    assert invoke(runner, tmp_path, "change", "verify", "add-passkey").exit_code == 0
    assert invoke(runner, tmp_path, "change", "sync", "add-passkey").exit_code == 0
    assert "通行密钥" in first.read_text(encoding="utf-8")
    assert "硬件令牌" in second.read_text(encoding="utf-8")

    synced_first = first.read_bytes()
    synced_second = second.read_bytes()
    assert invoke(runner, tmp_path, "change", "sync", "add-passkey").exit_code == 0
    assert first.read_bytes() == synced_first
    assert second.read_bytes() == synced_second

    # archive 只移动并登记 change，不会覆盖 sync 后的 spec 内容。
    first.write_text(
        first.read_text(encoding="utf-8") + "\n## [audit] 审计\n\n保留外部编辑。\n",
        encoding="utf-8",
    )
    externally_updated = first.read_bytes()
    result = invoke(runner, tmp_path, "change", "archive", "add-passkey")
    assert result.exit_code == 0, result.output
    assert first.read_bytes() == externally_updated


def test_rejected_and_invalid_state_transitions(tmp_path: Path) -> None:
    """覆盖 reject/remove 状态迁移和禁止的生命周期动作。"""

    runner = CliRunner()
    initialize(runner, tmp_path)
    assert (
        invoke(
            runner, tmp_path, "change", "create", "refactor", "discard-cache"
        ).exit_code
        == 0
    )
    assert invoke(runner, tmp_path, "change", "sync", "discard-cache").exit_code == 1
    assert invoke(runner, tmp_path, "change", "archive", "discard-cache").exit_code == 1
    result = invoke(
        runner, tmp_path, "change", "reject", "discard-cache", "--reason", "已不需要"
    )
    assert result.exit_code == 0, result.output
    rejected = tmp_path / "spec/changes/rejected/refactor/discard-cache"
    assert (rejected / "change.md").is_file()
    assert invoke(runner, tmp_path, "change", "status", "discard-cache").exit_code == 0
    assert invoke(runner, tmp_path, "change", "sync", "discard-cache").exit_code == 1
    assert invoke(runner, tmp_path, "change", "archive", "discard-cache").exit_code == 1
    assert (
        invoke(
            runner,
            tmp_path,
            "change",
            "reject",
            "discard-cache",
            "--reason",
            "再次拒绝",
        ).exit_code
        == 1
    )
    assert (
        invoke(runner, tmp_path, "change", "implement", "discard-cache").exit_code == 1
    )
    assert invoke(runner, tmp_path, "change", "verify", "discard-cache").exit_code == 0
    assert (
        invoke(runner, tmp_path, "change", "remove", "discard-cache", "--yes").exit_code
        == 0
    )
    assert not rejected.exists()
    assert list((tmp_path / ".trash").rglob("discard-cache"))


def test_proposed_remove_requires_confirmation(tmp_path: Path) -> None:
    """确认 proposed change 的 remove 可以确认、拒绝或显式跳过提示。"""

    runner = CliRunner()
    initialize(runner, tmp_path)
    assert (
        invoke(
            runner, tmp_path, "change", "create", "refactor", "temporary-work"
        ).exit_code
        == 0
    )
    proposed = tmp_path / "spec/changes/proposed/refactor/temporary-work"

    declined = runner.invoke(
        main,
        ["--root", str(tmp_path), "change", "remove", "temporary-work"],
        input="n\n",
    )
    assert declined.exit_code != 0
    assert proposed.is_dir()

    confirmed = runner.invoke(
        main,
        ["--root", str(tmp_path), "change", "remove", "temporary-work"],
        input="y\n",
    )
    assert confirmed.exit_code == 0
    assert not proposed.exists()
    assert list((tmp_path / ".trash").rglob("temporary-work"))


def test_post_sync_delta_edit_is_rejected_and_archive_does_not_replay(
    tmp_path: Path,
) -> None:
    """确认 sync 后 delta 固定，archive 发现过期回执时不改 spec。"""

    runner = CliRunner()
    initialize(runner, tmp_path)
    result = invoke(
        runner,
        tmp_path,
        "change",
        "create",
        "feat",
        "add-login",
        "--affect",
        "capability:login:create",
    )
    assert result.exit_code == 0, result.output
    change_dir = tmp_path / "spec/changes/proposed/feat/add-login"
    delta = change_dir / "deltas/capability/login.md"
    delta.write_text(
        "# delta\n\n## [ADDED] [login] 登录\n\n用户可以登录。\n", encoding="utf-8"
    )
    complete_tasks(change_dir)
    assert invoke(runner, tmp_path, "change", "verify", "add-login").exit_code == 0
    assert invoke(runner, tmp_path, "change", "implement", "add-login").exit_code == 0
    change_dir = tmp_path / "spec/changes/implemented/feat/add-login"
    delta = change_dir / "deltas/capability/login.md"
    assert invoke(runner, tmp_path, "change", "archive", "add-login").exit_code == 1
    assert invoke(runner, tmp_path, "change", "sync", "add-login").exit_code == 0

    spec = tmp_path / "spec/specs/capability/login/spec.md"
    before = spec.read_bytes()
    delta.write_text(
        "# delta\n\n## [ADDED] [login] 登录\n\n用户可以使用密码登录。\n",
        encoding="utf-8",
    )
    result = invoke(runner, tmp_path, "change", "archive", "add-login")
    assert result.exit_code == 1
    assert "回执已过期" in result.output
    assert spec.read_bytes() == before
    assert change_dir.is_dir()
