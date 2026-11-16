"""Specify 命令行入口；命令只负责参数解析和服务编排。"""

from __future__ import annotations

import json
import shutil
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from .archive import archive_change, validate_archived
from .baseline import capture_baselines
from .config import dump_yaml, load_config
from .contract import ContractIdentity
from .errors import EnvironmentError, ExitCode, SpecifyError, UsageError
from .index import build_index
from .io import move_to_trash
from .models import Change, Issue
from .parse.spec import parse_spec_file
from .paths import RepoPaths, find_change, validate_id
from .scaffold import create_change, create_spec, initialize
from .status import HumanStatus, ProjectStatus
from .sync import sync_change
from .validate.changes import read_metadata, validate_change, validate_changes
from .validate.specs import validate_specs


class CommandOutput:
    """统一处理人类输出、JSON 报告和 Specify 退出码。"""

    @staticmethod
    def emit(
        context: click.Context,
        message: str = "",
        issues: list[Issue] | None = None,
        ok: bool = True,
    ) -> None:
        """按全局 --json 选项输出结果，验证问题写入 stderr。"""

        if context.obj.get("json"):
            payload: dict[str, Any] = {
                "ok": ok,
                "issues": [issue.as_dict() for issue in (issues or [])],
            }
            if message:
                payload["message"] = message
            click.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return

        if message:
            click.echo(message)
        for issue in issues or []:
            prefix = f"{issue.path}: " if issue.path else ""
            click.echo(f"- {prefix}{issue.message}", err=True)

    @classmethod
    def fail(cls, context: click.Context, error: SpecifyError) -> None:
        """把领域错误转成稳定 JSON/文本输出和协议退出码。"""

        cls.emit(context, str(error), [Issue(error.message, error.path)], False)
        raise click.exceptions.Exit(error.code)


def project_paths(context: click.Context) -> RepoPaths:
    """读取命令根目录并确认项目已初始化。"""

    paths = RepoPaths(context.obj["root"])
    paths.require_config()
    return paths


class SpecifyGroup(click.Group):
    """统一把未包装的文件系统异常转换为环境错误退出码。"""

    def invoke(self, context: click.Context) -> Any:
        """执行命令树，并把文件系统错误按文本或 JSON 报告。"""

        try:
            return super().invoke(context)
        except OSError as error:
            issue = Issue(str(error))
            if context.obj and context.obj.get("json"):
                CommandOutput.emit(context, "文件系统操作失败", [issue], False)
                raise click.exceptions.Exit(ExitCode.ENVIRONMENT) from error
            raise SpecifyIOError(str(error)) from error


class SpecifyIOError(click.ClickException):
    """让未包装的 IO 错误使用 Specify 环境错误退出码。"""

    exit_code = ExitCode.ENVIRONMENT


@click.group(cls=SpecifyGroup)
@click.option(
    "--root",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
)
@click.option("--json", "json_output", is_flag=True, help="输出机器可读 JSON 报告。")
@click.version_option()
@click.pass_context
def main(context: click.Context, root: Path, json_output: bool) -> None:
    """管理 Contract spec 与 change 生命周期。"""

    context.ensure_object(dict)
    context.obj.update(root=root.resolve(), json=json_output)


@main.command("init")
@click.argument(
    "path", type=click.Path(file_okay=False, path_type=Path), default=Path(".")
)
@click.option(
    "--config", "config_path", type=click.Path(dir_okay=False, path_type=Path)
)
@click.pass_context
def init_command(context: click.Context, path: Path, config_path: Path | None) -> None:
    """用给定配置或内置默认值初始化项目目录。"""

    try:
        initialize(path.resolve(), config_path.resolve() if config_path else None)
        CommandOutput.emit(context, f"已初始化 Specify 项目：{path.resolve()}")
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@main.command("create")
@click.argument("spec_type")
@click.argument("spec_id")
@click.pass_context
def create_command(context: click.Context, spec_type: str, spec_id: str) -> None:
    """创建带显式 Contract ID 占位符的 formal spec。"""

    try:
        paths = project_paths(context)
        target = create_spec(paths, load_config(paths), spec_type, spec_id)
        CommandOutput.emit(context, f"已创建 {target}")
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@main.group("index")
def index_group() -> None:
    """管理由 formal specs 派生的索引。"""


@index_group.command("build")
@click.pass_context
def index_build(context: click.Context) -> None:
    """重建 spec/spec-index.md。"""

    try:
        paths = project_paths(context)
        build_index(paths, load_config(paths))
        CommandOutput.emit(context, f"已重建 {paths.index}")
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@main.group("change")
def change_group() -> None:
    """管理 change 草稿、实现、同步和归档。"""


@change_group.command("create")
@click.argument("kind")
@click.argument("change_id")
@click.option(
    "--affect", multiple=True, help="目标格式：type:spec-id:create|modify|remove。"
)
@click.pass_context
def change_create(
    context: click.Context, kind: str, change_id: str, affect: tuple[str, ...]
) -> None:
    """创建 proposed change 和可编辑文件骨架。"""

    try:
        paths = project_paths(context)
        target = create_change(paths, load_config(paths), kind, change_id, affect)
        CommandOutput.emit(context, f"已创建 {target}")
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@change_group.command("baseline")
@click.argument("change_id")
@click.pass_context
def change_baseline(context: click.Context, change_id: str) -> None:
    """显式读取当前正文并更新 change 的 baseVersions。"""

    try:
        paths = project_paths(context)
        change = find_change(paths, change_id)
        baselines = capture_baselines(paths, change)
        CommandOutput.emit(context, f"已捕获 {len(baselines)} 条 Contract 基线")
    except SpecifyError as error:
        CommandOutput.fail(context, error)


def inspect_change(
    context: click.Context,
    change_id: str,
    action: Callable[[Change, list[Issue]], None],
) -> None:
    """为 status/verify 读取 change 并复用同一套只读校验。"""

    try:
        paths = project_paths(context)
        change = find_change(paths, change_id)
        issues = validate_change(paths, load_config(paths), change)
        action(change, issues)
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@change_group.command("status")
@click.argument("change_id")
@click.pass_context
def change_status(context: click.Context, change_id: str) -> None:
    """显示目录状态和校验结果。"""

    def report(change: Change, issues: list[Issue]) -> None:
        """输出 change 当前状态和可读性校验结果。"""

        valid = not issues
        CommandOutput.emit(
            context,
            f"{change.id}: {change.status}/{change.kind} ({'valid' if valid else 'invalid'})",
            issues,
            valid,
        )
        if issues:
            raise click.exceptions.Exit(ExitCode.VALIDATION)

    inspect_change(context, change_id, report)


@change_group.command("verify")
@click.argument("change_id")
@click.pass_context
def change_verify(context: click.Context, change_id: str) -> None:
    """只读检查 metadata、tasks、delta 和基线。"""

    def report(_change: Change, issues: list[Issue]) -> None:
        """输出验证结果并使用约定的内容错误退出码。"""

        valid = not issues
        message = "change 校验通过" if valid else "change 校验失败"
        CommandOutput.emit(context, message, issues, valid)
        if issues:
            raise click.exceptions.Exit(ExitCode.VALIDATION)

    inspect_change(context, change_id, report)


@change_group.command("implement")
@click.argument("change_id")
@click.pass_context
def change_implement(context: click.Context, change_id: str) -> None:
    """任务完成且校验通过后将 change 移到 implemented。"""

    try:
        paths = project_paths(context)
        config = load_config(paths)
        change = find_change(paths, change_id)
        if change.status != "proposed":
            raise SpecifyError("只有 proposed change 可以标记为 implemented")
        issues = validate_change(paths, config, change, require_complete_tasks=True)
        if issues:
            CommandOutput.emit(
                context, "change 尚不能标记为 implemented", issues, False
            )
            raise click.exceptions.Exit(ExitCode.VALIDATION)
        metadata = read_metadata(change)
        metadata["updatedAt"] = (
            datetime.now().astimezone().isoformat(timespec="seconds")
        )
        dump_yaml(change.path / "meta-data.yaml", metadata)
        destination = paths.changes / "implemented" / change.kind / change.id
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(change.path), str(destination))
        CommandOutput.emit(context, f"已标记为 implemented：{change.id}")
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@change_group.command("reject")
@click.argument("change_id")
@click.option("--reason", required=True)
@click.pass_context
def change_reject(context: click.Context, change_id: str, reason: str) -> None:
    """保存拒绝理由，并将 proposed change 移到 rejected。"""

    try:
        if not reason.strip():
            raise SpecifyError("拒绝理由不能为空")
        paths = project_paths(context)
        change = find_change(paths, change_id)
        if change.status != "proposed":
            raise SpecifyError("只有 proposed change 可以被拒绝")
        metadata = read_metadata(change)
        metadata["rejectedReason"] = reason.strip()
        metadata["updatedAt"] = (
            datetime.now().astimezone().isoformat(timespec="seconds")
        )
        dump_yaml(change.path / "meta-data.yaml", metadata)
        destination = paths.changes / "rejected" / change.kind / change.id
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(change.path), str(destination))
        CommandOutput.emit(context, f"已拒绝 {change.id}")
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@change_group.command("remove")
@click.argument("change_id")
@click.option("--yes", is_flag=True, help="跳过确认。")
@click.pass_context
def change_remove(context: click.Context, change_id: str, yes: bool) -> None:
    """将可移除的 proposed/rejected change 移入项目 .trash。"""

    try:
        paths = project_paths(context)
        change = find_change(paths, change_id)
        if change.status not in {"proposed", "rejected"}:
            raise SpecifyError("只能移除 proposed 或 rejected change")
        if not yes and not click.confirm(
            f"将 {change.id} 移入 .trash？", default=False
        ):
            raise click.exceptions.Abort()
        destination = move_to_trash(change.path, paths.root)
        CommandOutput.emit(context, f"已移入 {destination}")
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@change_group.command("sync")
@click.argument("change_id")
@click.pass_context
def change_sync(context: click.Context, change_id: str) -> None:
    """将 implemented change 当前 delta 同步到 formal specs。"""

    try:
        paths = project_paths(context)
        change = find_change(paths, change_id)
        changed = sync_change(paths, change)
        if changed:
            message = f"已同步 {change.id}"
        else:
            message = f"{change.id} 已同步或不影响 formal specs，无需写入"
        CommandOutput.emit(context, message)
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@change_group.command("archive")
@click.argument("change_id")
@click.pass_context
def change_archive(context: click.Context, change_id: str) -> None:
    """仅移动已同步的 change 并登记归档文件，不重放 delta。"""

    try:
        paths = project_paths(context)
        change = find_change(paths, change_id)
        destination = archive_change(paths, change)
        CommandOutput.emit(context, f"已归档 {change.id}：{destination}")
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@main.command("validate")
@click.option("--specs", "specs_only", is_flag=True)
@click.option("--changes", "changes_only", is_flag=True)
@click.option("--archived", "archived_only", is_flag=True)
@click.pass_context
def validate_command(
    context: click.Context,
    specs_only: bool,
    changes_only: bool,
    archived_only: bool,
) -> None:
    """按指定范围校验正式 spec、change 或归档历史。"""

    try:
        paths = project_paths(context)
        config = load_config(paths)
        selected = sum((specs_only, changes_only, archived_only))
        if selected > 1:
            raise SpecifyError("--specs、--changes、--archived 最多只能选择一个")

        issues: list[Issue] = []
        if not changes_only and not archived_only:
            issues.extend(validate_specs(paths, config))
        if not specs_only and not archived_only:
            issues.extend(validate_changes(paths, config))
        if not specs_only and not changes_only:
            issues.extend(validate_archived(paths))
        valid = not issues
        CommandOutput.emit(context, "校验通过" if valid else "校验失败", issues, valid)
        if issues:
            raise click.exceptions.Exit(ExitCode.VALIDATION)
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@main.command("list")
@click.option("--type", "spec_type")
@click.option(
    "--change", "list_changes", is_flag=True, help="列出活跃 change（默认）。"
)
@click.option("--spec", "list_formal_specs", is_flag=True, help="列出正式 spec。")
@click.option("--human", is_flag=True, help="用表格展示列表。")
@click.pass_context
def list_command(
    context: click.Context,
    spec_type: str | None,
    list_changes: bool,
    list_formal_specs: bool,
    human: bool,
) -> None:
    """默认以 JSON 列出活跃 change，并按选项切换正式 spec 与人类表格。"""

    try:
        if human and context.obj["json"]:
            raise UsageError("--human 与 --json 不能同时使用")
        if list_changes and list_formal_specs:
            raise UsageError("--change 与 --spec 不能同时使用")
        if spec_type and not list_formal_specs:
            raise UsageError("--type 只能与 --spec 一起使用")
        paths = project_paths(context)
        config = load_config(paths)
        if spec_type and spec_type not in config["specTypes"]:
            raise SpecifyError(f"未知 spec type：{spec_type}")
        status = ProjectStatus(paths).read()
        if list_formal_specs:
            items = [
                item
                for item in status["specs"]
                if spec_type is None or item["type"] == spec_type
            ]
            if human:
                HumanStatus(Console(file=sys.stdout)).specs(items)
            else:
                click.echo(
                    json.dumps({"specs": items}, ensure_ascii=False, sort_keys=True)
                )
        else:
            items = [
                item
                for item in status["changes"]
                if item["status"] in {"proposed", "implemented"}
            ]
            if human:
                HumanStatus(Console(file=sys.stdout)).changes(items)
            else:
                click.echo(
                    json.dumps({"changes": items}, ensure_ascii=False, sort_keys=True)
                )
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@main.command("status")
@click.option("--human", is_flag=True, help="用表格展示正式 spec 和 change 状态。")
@click.pass_context
def status_command(context: click.Context, human: bool) -> None:
    """查询项目状态；默认输出 JSON，Rich 展示需显式指定。"""

    try:
        if human and context.obj["json"]:
            raise UsageError("--human 与 --json 不能同时使用")
        status = ProjectStatus(project_paths(context)).read()
        if human:
            presenter = HumanStatus(Console(file=sys.stdout))
            presenter.specs(status["specs"])
            presenter.changes(status["changes"])
        else:
            click.echo(json.dumps(status, ensure_ascii=False, sort_keys=True))
    except SpecifyError as error:
        CommandOutput.fail(context, error)


@main.command("show")
@click.argument("reference")
@click.pass_context
def show_command(context: click.Context, reference: str) -> None:
    """展示一个 formal spec，并在 JSON 中附带正文基线 hash。"""

    try:
        parts = reference.split(":")
        if len(parts) != 2 or not validate_id(parts[1]):
            raise UsageError("show 参数必须是 <type>:<spec-id>")
        paths = project_paths(context)
        if parts[0] not in load_config(paths)["specTypes"]:
            raise UsageError(f"未知 spec type：{parts[0]}")
        target = paths.specs / parts[0] / parts[1] / "spec.md"
        if not target.is_file():
            raise EnvironmentError(f"找不到 spec：{reference}", str(target))

        document = parse_spec_file(target)
        if context.obj["json"]:
            contracts = [
                {
                    "id": contract.id,
                    "title": contract.title,
                    "body": contract.body,
                    "bodyHash": ContractIdentity.body_hash(contract.body),
                }
                for contract in document.contracts
            ]
            click.echo(
                json.dumps(
                    {"type": parts[0], "id": parts[1], "contracts": contracts},
                    ensure_ascii=False,
                )
            )
        else:
            click.echo(target.read_text(encoding="utf-8"), nl=False)
    except SpecifyError as error:
        CommandOutput.fail(context, error)


if __name__ == "__main__":
    main()
