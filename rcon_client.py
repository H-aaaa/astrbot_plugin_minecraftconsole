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


class RconError(Exception):
    pass


class RconAuthError(RconError):
    pass


class RconProtocolError(RconError):
    pass


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

    async def _roundtrip(self, request_line: str) -> dict[str, str]:
        reader = None
        writer = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.cfg.host, self.cfg.port),
                timeout=self.cfg.timeout,
            )
            writer.write((self.cfg.password + "\n").encode("utf-8"))
            writer.write((request_line + "\n").encode("utf-8"))
            await asyncio.wait_for(writer.drain(), timeout=self.cfg.timeout)

            result: dict[str, str] = {}
            while True:
                raw = await asyncio.wait_for(reader.readline(), timeout=self.cfg.timeout)
                if not raw:
                    raise RconProtocolError("Bridge connection closed unexpectedly")
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line == "end=1":
                    break
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                result[key] = value
            return result
        except asyncio.TimeoutError as e:
            raise RconError("Bridge read/write timeout") from e
        finally:
            if writer is not None:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

    @staticmethod
    def _decode_output(result: dict[str, str]) -> str:
        if "output_b64" in result:
            try:
                return base64.b64decode(result["output_b64"]).decode("utf-8", errors="replace")
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
            raise RconError(code or "Bridge ping failed")
        self._tested = True

    async def ensure_ready(self) -> None:
        if self.cfg.test_on_first_use and not self._tested:
            await self.auth()

    async def exec(self, command: str, wait_ms: int = 0) -> str:
        await self.ensure_ready()
        data = await self._roundtrip(f"EXEC|{max(0, int(wait_ms))}|{command}")
        if data.get("status") != "ok":
            code = str(data.get("code", ""))
            if code == "AUTH_FAILED":
                raise RconAuthError("Bridge auth failed")
            raise RconError(code or "Bridge exec failed")
        return self._decode_output(data).strip("\n")
