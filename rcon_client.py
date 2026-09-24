"""异步桥接客户端。

协议：
1. 连接后先发送 token + 换行
2. 再发送单行请求：
   - PING
   - EXEC|<wait_ms>|<command>
3. 服务端返回多行：
   - status=ok|error
   - code=...
   - output_b64=...
   - end=1
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass


# 桥接端最多返回 65536 个字符，UTF-8 + Base64 后可能超过 asyncio 默认的 64 KiB。
MAX_RESPONSE_LINE_BYTES = 512 * 1024
# 桥接端最多等待其他命令 10 秒，再等待服务端调度 10 秒。
COMMAND_SCHEDULING_TIMEOUT = 20.0


class RconError(Exception):
    pass


class RconConnectionError(RconError):
    """尚未建立连接，当前命令没有发送，可以重试。"""


class RconAuthError(RconError):
    pass


class RconProtocolError(RconError):
    pass


class RconResponseError(RconError):
    def __init__(self, code: str, output: str):
        super().__init__(code)
        self.code = code
        self.output = output


@dataclass(frozen=True)
class RconConfig:
    host: str
    port: int
    password: str
    timeout: float = 5.0
    test_on_first_use: bool = True


class AsyncRconClient:
    def __init__(self, cfg: RconConfig):
        self.cfg = cfg
        self._tested = False

    async def close(self) -> None:
        self._tested = False

    async def _roundtrip(
        self, request_line: str, response_timeout: float | None = None
    ) -> dict[str, str]:
        writer = None
        try:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(
                        self.cfg.host, self.cfg.port, limit=MAX_RESPONSE_LINE_BYTES
                    ),
                    timeout=self.cfg.timeout,
                )
            except (OSError, asyncio.TimeoutError) as e:
                raise RconConnectionError("Bridge connection failed") from e

            writer.write((self.cfg.password + "\n").encode("utf-8"))
            writer.write((request_line + "\n").encode("utf-8"))
            await asyncio.wait_for(writer.drain(), timeout=self.cfg.timeout)

            result: dict[str, str] = {}
            loop = asyncio.get_running_loop()
            deadline = loop.time() + (
                self.cfg.timeout if response_timeout is None else response_timeout
            )
            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise asyncio.TimeoutError
                raw = await asyncio.wait_for(reader.readline(), timeout=remaining)
                if not raw:
                    raise RconProtocolError("Bridge connection closed unexpectedly")
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line == "end=1":
                    break
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                result[key] = value
            if result.get("status") not in ("ok", "error") or "code" not in result:
                raise RconProtocolError("Invalid bridge response")
            return result
        except asyncio.TimeoutError as e:
            raise RconError("Bridge read/write timeout") from e
        finally:
            if writer is not None:
                try:
                    writer.close()
                    await asyncio.wait_for(writer.wait_closed(), timeout=self.cfg.timeout)
                except Exception:
                    pass

    @staticmethod
    def _decode_output(result: dict[str, str]) -> str:
        if "output_b64" in result:
            try:
                return base64.b64decode(result["output_b64"], validate=True).decode(
                    "utf-8", errors="replace"
                )
            except Exception as e:
                raise RconProtocolError("Invalid output_b64 payload") from e
        if "output" in result:
            try:
                return base64.b64decode(result["output"]).decode("utf-8", errors="replace")
            except Exception:
                return result["output"]
        return ""

    async def auth(self) -> None:
        data = await self._roundtrip("PING")
        if data.get("status") != "ok":
            code = str(data.get("code", ""))
            if code == "AUTH_FAILED":
                raise RconAuthError("Bridge auth failed")
            raise RconResponseError(code or "Bridge ping failed", self._decode_output(data))
        self._tested = True

    async def ensure_ready(self) -> None:
        if self.cfg.test_on_first_use and not self._tested:
            await self.auth()

    async def exec(self, command: str, wait_ms: int = 0) -> str:
        await self.ensure_ready()
        wait_ms = max(0, int(wait_ms))
        # 日志采集时间与服务端排队时间不占用网络超时预算。
        data = await self._roundtrip(
            f"EXEC|{wait_ms}|{command}",
            response_timeout=self.cfg.timeout + COMMAND_SCHEDULING_TIMEOUT + wait_ms / 1000,
        )
        if data.get("status") != "ok":
            code = str(data.get("code", ""))
            if code == "AUTH_FAILED":
                raise RconAuthError("Bridge auth failed")
            raise RconResponseError(code or "Bridge exec failed", self._decode_output(data))
        return self._decode_output(data).strip("\n")
