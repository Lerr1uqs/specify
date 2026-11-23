"""验证 Review 页的差异来源、只读行为与 CLI 入口。"""

from http import HTTPStatus
from pathlib import Path
from shutil import copytree

from click.testing import CliRunner
from pytest import MonkeyPatch

from specify.cli import main
from specify.paths import RepoPaths
from specify.web import ReviewPage

EXAMPLE = Path(__file__).resolve().parents[1] / "example_specs"


def test_review_reads_current_specs_and_pending_delta() -> None:
    """正式正文和未同步预览分别显示，合法基线不报冲突。"""

    page = ReviewPage(RepoPaths(EXAMPLE))
    status, spec = page.render({"spec": ["capability:account-recovery"]})
    assert status == HTTPStatus.OK
    assert "当前正式 Spec" in spec and "request-recovery" in spec
    assert "<p>" in spec and "<li>" in spec
    status, change = page.render({"change": ["show-recovery-delivery-state"]})
    assert status == HTTPStatus.OK
    assert "尚未生效" in change and "capability:account-recovery" in change
    assert '<span class="insert">+' in change and '<span class="delete">-' in change
    assert "尚未捕获正文基线" not in change and "正文基线已变化" not in change


def test_review_shows_dates_from_change_receipt_and_archive_manifest() -> None:
    """各状态只显示已记录的时间，兼容 YAML 时间戳和字符串。"""

    page = ReviewPage(RepoPaths(EXAMPLE))
    _, processing = page.render({"change": ["show-recovery-delivery-state"]})
    assert "<dt>创建</dt>" in processing and "<dt>更新</dt>" in processing
    assert "<dt>同步</dt>" not in processing and "<dt>归档</dt>" not in processing

    _, synced = page.render({"change": ["add-passkey-login"]})
    assert '<dt>同步</dt><dd><time datetime="2026-11-15T14:30:00+08:00">' in synced
    assert "<dt>归档</dt>" not in synced

    _, archived = page.render({"change": ["reorganize-auth-files"]})
    assert '<dt>归档</dt><dd><time datetime="2026-11-15T15:00:00+08:00">' in archived
    assert "<dt>同步</dt>" not in archived


def test_review_sorts_and_filters_change_priorities(tmp_path: Path) -> None:
    """同组按优先级排队，P2 筛选包含旧草稿但隐藏 P4。"""

    copytree(EXAMPLE / "spec", tmp_path / "spec")
    runner = CliRunner()
    for change_id, priority in (
        ("show-recovery-delivery-state", "P0"),
        ("extend-audit-retention-to-90-days", "P4"),
    ):
        result = runner.invoke(
            main, ["--root", str(tmp_path), "change", "priority", change_id, priority]
        )
        assert result.exit_code == 0, result.output

    page = ReviewPage(RepoPaths(tmp_path))
    _, all_changes = page.render({"change": [""]})
    sidebar = all_changes.split('<nav class="sidebar"', 1)[1].split("</nav>", 1)[0]
    assert sidebar.index("show-recovery-delivery-state") < sidebar.index(
        "extend-audit-retention-to-60-days"
    )
    assert 'class="priority-badge p0">P0' in sidebar
    assert 'class="priority-badge p4">P4' in sidebar

    status, filtered = page.render(
        {"change": ["extend-audit-retention-to-90-days"], "priority": ["P2"]}
    )
    assert status == HTTPStatus.OK
    assert "extend-audit-retention-to-90-days" not in filtered
    assert '<span class="priority-value">P2 及以上</span>' in filtered
    assert (
        'priority=P2" aria-current="true"><span class="priority-badge p2">P2'
        in filtered
    )
    assert 'class="priority-badge p2">P2' in filtered
    assert (
        'change=preview-audit-export&amp;priority=P2" aria-current="page"' in filtered
    )


def test_review_proposed_only_renders_requirement() -> None:
    """待拆解需求直接渲染 Markdown，省去实施状态的任务和影响树。"""

    status, page = ReviewPage(RepoPaths(EXAMPLE)).render(
        {"change": ["preview-audit-export"]}
    )
    assert status == HTTPStatus.OK
    assert 'class="card proposal-document" tabindex="0"' in page
    assert "<h2>Requirement</h2>" in page and "预计记录数" in page
    assert "task-progress" not in page and "impact-tree" not in page


def test_review_shows_task_progress_without_conflating_sync(tmp_path: Path) -> None:
    """进度取自任务文件；任务无效时仍可查看影响树，完成任务也不等于同步。"""

    copytree(EXAMPLE / "spec", tmp_path / "spec")
    page = ReviewPage(RepoPaths(tmp_path))
    example = "show-recovery-delivery-state"
    _, pending = page.render({"change": [example]})
    assert 'value="1" max="2">50%</progress>' in pending
    assert "已完成 1 / 2 · 50%" in pending and "待完成" in pending
    assert '<section class="change-description"><h3>变更说明</h3>' in pending
    assert '<section class="task-progress">' in pending
    assert "<h1>显示恢复申请处理进度</h1>" not in pending
    _, complete = page.render({"change": ["explain-delivery-receipt-outcomes"]})
    assert 'value="2" max="2">100%</progress>' in complete and "尚未生效" in complete

    path = page.changes[example].path / "tasks.md"
    path.write_text("# tasks\n\n- [x] 没有编号\n", encoding="utf-8")
    _, invalid = page.render({"change": [example]})
    assert "任务进度不可用" in invalid and "第 3 行的 task 格式无效" in invalid
    assert "<progress" not in invalid and 'class="impact-tree"' in invalid


def test_review_uses_the_matching_historical_event(tmp_path: Path) -> None:
    """归档删除不被后来的同 ID 新增污染；重命名和改正文共享一份 diff。"""

    page = ReviewPage(RepoPaths(EXAMPLE))
    _, archived = page.render({"change": ["publish-recovery-controls"]})
    assert "历史差异" in archived
    assert '<span class="delete">-## 恢复验证次数限制' in archived
    assert "跨入口共享恢复尝试次数" not in archived
    assert '<span class="insert">+## 恢复校验与通知数据流' in archived
    assert 'class="pill renamed">重命名' in archived
    # 根节点、Spec 分支和不同类型的 Contract 边使用同一份可展开 DOM。
    assert (
        'class="impact-source"><strong>Change</strong><code>publish-recovery-controls'
        in archived
    )
    assert '<script src="/review.js" defer>' in archived
    assert '<svg class="impact-curves" aria-hidden="true">' in archived
    assert archived.count('class="impact-contracts"') == 4
    for action in ("modified", "added", "removed"):
        assert f'<li class="{action}"><details class="operation" ' in archived
    assert "已落后当前 Spec" in archived
    _, restored = page.render({"change": ["restore-recovery-attempt-limits"]})
    assert '<span class="insert">+## 跨入口共享恢复尝试次数' in restored
    assert '<span class="delete">' not in restored

    _, recovered = page.render({"change": ["add-passkey-login"]})
    assert (
        '<span class="delete">-认证服务负责验证密码凭据，并返回认证结果。' in recovered
    )
    assert '<span class="insert">+## 通行密钥登录' in recovered
    assert "没有可还原的当次同步快照" not in recovered

    # 有早期回执但快照丢失时，保留 delta 声明。
    copytree(EXAMPLE / "spec", tmp_path / "spec")
    legacy_page = ReviewPage(RepoPaths(tmp_path))
    path = legacy_page.changes["add-passkey-login"].path / "meta-data.yaml"
    metadata = path.read_text(encoding="utf-8")
    path.write_text(metadata.split("  historyId:")[0], encoding="utf-8")
    _, legacy = legacy_page.render({"change": ["add-passkey-login"]})
    assert "没有可还原的当次同步快照" in legacy and "credential-validation" in legacy
    assert 'class="diff"' not in legacy
    _, rejected = page.render({"change": ["expose-recovery-lookup-result"]})
    assert "拒绝原因" in rejected and 'class="diff"' not in rejected
    _, no_impact = page.render({"change": ["reorganize-auth-files"]})
    assert "不影响正式 Spec" in no_impact


def test_review_shows_receipt_lifecycle() -> None:
    """归档新增和删除使用各自时点；未同步预览不改变正式 Spec。"""

    page = ReviewPage(RepoPaths(EXAMPLE))
    _, launch = page.render({"change": ["launch-delivery-receipts"]})
    assert 'class="pill">新增 Spec' in launch
    assert '<span class="insert">+## 试点渠道' in launch
    _, retire = page.render({"change": ["retire-receipt-pilot"]})
    assert 'class="pill">删除 Spec' in retire
    assert '<span class="delete">-## 试点渠道' in retire
    assert '<span class="delete">-## 试点结束条件' in retire
    _, pending = page.render({"change": ["explain-delivery-receipt-outcomes"]})
    assert "尚未生效" in pending and '<li class="renamed">' in pending
    assert '<span class="insert">+## 查看通知回执' in pending
    assert "data-toggle-diffs hidden>展开全部</button>" in pending
    assert (
        'href="/?spec=capability%3Adelivery-receipts" aria-controls="current-spec-panel"'
        in pending
    )
    assert 'href="/?spec=rule%3Areceipt-retention"' not in pending
    assert '</ul><aside id="current-spec-panel"' in pending
    _, current = page.render({"spec": ["capability:delivery-receipts"]})
    assert "查询通知回执" in current and "查看通知回执" not in current
    assert (
        "rule:receipt-pilot" not in page.specs
        and "rule:receipt-retention" not in page.specs
    )


def test_review_marks_stale_baselines_and_never_writes(tmp_path: Path) -> None:
    """刷新读取人工修改，标出过期基线且不会执行仓库 Markdown 中的 HTML。"""

    copytree(EXAMPLE / "spec", tmp_path / "spec")
    path = tmp_path / "spec/specs/capability/account-recovery/spec.md"
    source = path.read_text(encoding="utf-8").replace(
        "## [reset-password]", "<script>alert(1)</script>\n\n## [reset-password]"
    )
    path.write_text(source, encoding="utf-8")
    before = {file: file.read_bytes() for file in tmp_path.rglob("*") if file.is_file()}
    page = ReviewPage(RepoPaths(tmp_path))
    _, spec = page.render({"spec": ["capability:account-recovery"]})
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in spec
    assert "<script>" not in spec
    _, change = page.render({"change": ["show-recovery-delivery-state"]})
    assert "正文基线已变化：" in change
    assert 'class="pill stale">已落后当前 Spec' in change
    assert (
        "data-current-contract>capability:account-recovery:request-recovery</button>"
        in change
    )
    dialog, _, diff = change.partition("</dialog>")
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in dialog
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" not in diff
    assert {
        file: file.read_bytes() for file in tmp_path.rglob("*") if file.is_file()
    } == before


def test_review_previews_creating_and_removing_entire_specs(tmp_path: Path) -> None:
    """同一 change 可预览新增和整份删除，当前 Spec 导航不提前改变。"""

    runner = CliRunner()
    assert runner.invoke(main, ["init", str(tmp_path)]).exit_code == 0
    paths = RepoPaths(tmp_path)
    formal = paths.specs / "rule" / "old" / "spec.md"
    formal.parent.mkdir(parents=True)
    formal.write_text("# contract\n\n## [rule] 旧规则\n\n旧正文\n", encoding="utf-8")
    result = runner.invoke(
        main,
        [
            "--root",
            str(tmp_path),
            "change",
            "create",
            "feat",
            "replace-rule",
            "--affect",
            "rule:old:remove",
            "--affect",
            "rule:new:create",
        ],
    )
    assert result.exit_code == 0, result.output
    deltas = paths.changes / "processing/feat/replace-rule/deltas/rule"
    (deltas / "old.md").write_text(
        "# delta\n\n## [REMOVED] [rule] 旧规则\n\n**Reason**: 规则替换。\n\n**Migration**: 使用新规则。\n",
        encoding="utf-8",
    )
    (deltas / "new.md").write_text(
        "# delta\n\n## [ADDED] [rule] 新规则\n\n新正文\n", encoding="utf-8"
    )
    page = ReviewPage(paths)
    _, change = page.render({"change": ["replace-rule"]})
    assert 'class="pill">删除 Spec' in change and 'class="pill">新增 Spec' in change
    assert '<span class="delete">-旧正文' in change
    assert '<span class="insert">+新正文' in change
    assert list(page.specs) == ["rule:old"] and formal.is_file()


def test_web_command_and_unknown_reference(monkeypatch: MonkeyPatch) -> None:
    """--root 传给服务，任意查询值只能查找既有项目引用。"""

    def start(paths: RepoPaths, announce: object) -> None:
        """替换阻塞式 HTTP 服务，验证 CLI 参数编排。"""

        assert paths.root == EXAMPLE
        assert callable(announce)

    monkeypatch.setattr("specify.cli.serve_review", start)
    result = CliRunner().invoke(main, ["--root", str(EXAMPLE), "web"])
    assert result.exit_code == 0, result.output
    status, page = ReviewPage(RepoPaths(EXAMPLE)).render({"spec": ["../<script>"]})
    assert status == HTTPStatus.NOT_FOUND and "../&lt;script&gt;" in page
