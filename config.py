"""配置管理模块"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MinecraftConsoleConfig:
    enabled: bool = True
    admins: list[str] = field(default_factory=list)

    # 沿用旧字段名，实际含义是桥接插件地址/端口/token
    rcon_host: str = "127.0.0.1"
    rcon_port: int = 25580
    rcon_password: str = ""
    timeout: float = 5.0

    # 网络重试，仅针对网络/鉴权/协议错误，不会因为空输出重复执行命令
    max_attempts: int = 2
    test_on_first_use: bool = True

    # 默认日志等待时间；若用户显式带 --t，则以用户值为准
    default_wait_ms: int = 300

    # 输出控制
    max_output: int = 1500

    def __post_init__(self):
        self.admins = self._parse_list(self.admins)
        self.max_attempts = self._to_int(self.max_attempts, 2, minimum=1)
        self.default_wait_ms = self._to_int(self.default_wait_ms, 300, minimum=0)
        self.max_output = self._to_int(self.max_output, 1500, minimum=1)
        try:
            self.timeout = max(1.0, float(self.timeout))
        except Exception:
            self.timeout = 5.0
        self.test_on_first_use = bool(self.test_on_first_use)

    @staticmethod
    def _to_int(value, default: int, minimum: int = 0) -> int:
        try:
            return max(minimum, int(value))
        except Exception:
            return default

    @staticmethod
    def _parse_list(value) -> list[str]:
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        if isinstance(value, str) and value.strip():
            return [
                line.strip()
                for line in value.split("\n")
                if line.strip() and not line.strip().startswith("#")
            ]
        return []

    @classmethod
    def from_dict(cls, config: dict) -> "MinecraftConsoleConfig":
        return cls(**{k: v for k, v in config.items() if k in cls.__annotations__})

    @property
    def is_rcon_ready(self) -> bool:
        return bool(self.rcon_host and self.rcon_port and self.rcon_password.strip())
