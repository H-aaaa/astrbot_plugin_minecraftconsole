"""辅助工具模块"""

from __future__ import annotations


def parse_command_args(event_message_str: str, command: str) -> str | None:
    """
    解析指令参数，并尽量保留参数的原始空白（不压缩空格）。

    兼容输入：
    1) "/mc-command say hello"
    2) "mc-command say hello"
    3) "say hello"（框架已剥离命令名）

    返回：只包含参数部分，例如 "say hello"
    """
    if event_message_str is None:
        return None

    # 仅去掉首尾换行/空白（不做 split()，避免压缩 JSON 内部空格）
    s = event_message_str.strip()
    if not s:
        return None

    # 兼容全角斜杠
    if s.startswith("／"):
        s = "/" + s[1:]

    cmd = command.strip().lstrip("/")
    cmd_lower = cmd.lower()

    # 情况1：以 "/cmd" 开头（不压缩空白）
    if s[: len(cmd) + 1].lower() == f"/{cmd_lower}":
        rest = s[len(cmd) + 1 :]
        rest = rest.lstrip()  # 只去掉命令后面的分隔空白
        return rest if rest else None

    # 情况2：以 "cmd" 开头（无斜杠）
    if s[: len(cmd)].lower() == cmd_lower:
        rest = s[len(cmd) :]
        rest = rest.lstrip()
        return rest if rest else None

    # 情况3：框架已剥离命令名，整串就是参数（保留内部空白）
    return s


def truncate_text(text: str, max_len: int) -> str:
    if text is None:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"\n...（已截断，原长度 {len(text)} 字符）"
