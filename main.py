"""AstrBot Minecraft Console Plugin
通过桥接插件执行 Minecraft 指令：/mc-command <command>
"""

from __future__ import annotations

import asyncio

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .config import MinecraftConsoleConfig
from .message_formatter import MessageFormatter
from .rcon_client import AsyncRconClient, RconAuthError, RconConfig, RconError
from .utils import parse_command_args, parse_exec_options, truncate_text


@register("minecraftconsole", "MineCraft控制台", "使用桥接服务发送命令至MC", "1.3.0")
class MinecraftConsole(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.context = context
        self.config = MinecraftConsoleConfig.from_dict(config)
        self.formatter = MessageFormatter()
        self._rcon_lock = asyncio.Lock()
        self._client: AsyncRconClient | None = None
        self._client_cfg: RconConfig | None = None

        if not self.config.enabled:
            logger.info("[MC-BRIDGE] 插件未启用")
        elif not self.config.is_rcon_ready:
            logger.warning("[MC-BRIDGE] 未配置 host/port/token，/mc-command 暂不可用")
        else:
            logger.info("[MC-BRIDGE] 插件已启用（按需连接桥接端）")

    async def initialize(self):
        if self.config.enabled and not self.config.is_rcon_ready:
            logger.warning("[MC-BRIDGE] token 为空，/mc-command 暂不可用")

    def _ensure_client(self) -> None:
        if not self.config.is_rcon_ready:
            self._client = None
            self._client_cfg = None
            return

        cfg = RconConfig(
            host=self.config.rcon_host,
            port=int(self.config.rcon_port),
            password=self.config.rcon_password,
            timeout=float(self.config.timeout),
            test_on_first_use=bool(self.config.test_on_first_use),
        )
        if self._client_cfg != cfg:
            self._client_cfg = cfg
            self._client = AsyncRconClient(cfg)

    def _is_admin(self, user_id) -> bool:
        if user_id is None:
            return False
        return str(user_id) in {str(x) for x in (self.config.admins or [])}

    async def _exec_with_retry(self, command: str, wait_ms: int) -> str:
        if self._client is None or self._client_cfg is None:
            raise RconError("client not ready")

        last_error: Exception | None = None
        for attempt in range(1, int(self.config.max_attempts) + 1):
            try:
                return await self._client.exec(command, wait_ms)
            except RconAuthError:
                await self._client.close()
                self._client = AsyncRconClient(self._client_cfg)
                raise
            except Exception as e:
                last_error = e
                logger.warning("[MC-BRIDGE] 第 %s/%s 次执行失败: %s", attempt, self.config.max_attempts, e)
                await self._client.close()
                self._client = AsyncRconClient(self._client_cfg)
                if attempt >= int(self.config.max_attempts):
                    break
        raise RconError(str(last_error) if last_error else "unknown error")

    @filter.command("mc-command")
    async def mc_command(self, event: AstrMessageEvent):
        logger.info("[MC-BRIDGE] raw event.message_str = %r", event.message_str)

        if not self.config.enabled:
            yield event.plain_result(self.formatter.format_not_enabled())
            return

        if not self._is_admin(event.get_sender_id()):
            yield event.plain_result(self.formatter.format_no_permission())
            return

        args = parse_command_args(event.message_str, "mc-command")
        if not args:
            yield event.plain_result(self.formatter.format_usage())
            return

        options = parse_exec_options(args)
        if not options.command:
            yield event.plain_result(self.formatter.format_usage())
            return

        wait_ms = options.wait_ms if options.explicit_wait else int(self.config.default_wait_ms)

        self._ensure_client()
        if self._client is None or self._client_cfg is None:
            yield event.plain_result(self.formatter.format_not_configured())
            return

        async with self._rcon_lock:
            try:
                output = await self._exec_with_retry(options.command, wait_ms)
                output = output if output else "(无输出)"
                output = truncate_text(output, int(self.config.max_output))
                yield event.plain_result(self.formatter.format_exec_result(options.command, output))
            except RconAuthError:
                yield event.plain_result(self.formatter.format_auth_failed())
            except Exception as e:
                logger.error("[MC-BRIDGE] 执行失败: %s", e, exc_info=True)
                yield event.plain_result(self.formatter.format_exec_failed())

    async def terminate(self):
        logger.info("[MC-BRIDGE] 正在停止插件...")
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
        logger.info("[MC-BRIDGE] 已停止")
