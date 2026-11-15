"""统一领域异常和 CLI 退出码。"""

from __future__ import annotations

from dataclasses import dataclass


class ExitCode:
    """集中声明协议退出码，避免命令间出现差异。"""

    OK = 0
    VALIDATION = 1
    USAGE = 2
    ENVIRONMENT = 3


@dataclass
class SpecifyError(Exception):
    """可安全展示给用户或 CI 的预期错误。"""

    message: str
    code: int = ExitCode.VALIDATION
    path: str | None = None

    def __str__(self) -> str:
        """把可选文件路径和错误原因组合成人类可读文本。"""

        return f"{self.path}: {self.message}" if self.path else self.message


class UsageError(SpecifyError):
    """表示命令语法有效但参数取值不符合要求。"""

    def __init__(self, message: str):
        super().__init__(message, ExitCode.USAGE)


class EnvironmentError(SpecifyError):
    """表示项目配置、依赖或文件系统资源缺失。"""

    def __init__(self, message: str, path: str | None = None):
        super().__init__(message, ExitCode.ENVIRONMENT, path)


def require(condition: bool, message: str, path: str | None = None) -> None:
    """条件不成立时抛出带文件上下文的验证错误。"""

    if not condition:
        raise SpecifyError(message, ExitCode.VALIDATION, path)
