# MineCraft 控制台 · AstrBot

在 AstrBot 聊天中发送 `/mc-command`，通过 [AstrBotRconBridge](https://github.com/H-aaaa/AstrBotRconBridge) 执行 Minecraft 控制台命令，并把服务端日志回传到聊天中。

```text
/mc-command list
/mc-command say hello
/mc-command lp editor --t=5s
```

插件使用桥接端的 TCP 协议。配置中的 `rcon_*` 是为了兼容旧配置保留的字段名，实际填写的是**桥接地址、桥接端口和 token**；无需在 `server.properties` 中启用原生 RCON。

## 使用前准备

- AstrBot v4，以及允许使用命令的聊天账号 ID。
- Minecraft 服务端安装 AstrBotRconBridge，AstrBot 能访问它的监听端口。
- 本文的日志采集说明对应桥接端的 [latest.log 采集更新](https://github.com/H-aaaa/AstrBotRconBridge/pull/1)。它使用真实控制台执行命令，再读取日志文件新增的内容。

Minecraft 核心的调度适配由桥接端负责：Folia 使用全局区域调度器，Paper、Leaves 使用相应接口，旧版 Bukkit/Spigot 使用主线程调度。Folia 上的第三方命令仍需要相应插件自身支持 Folia。

## 安装与配置

### 1. 配置 Minecraft 桥接端

将 AstrBotRconBridge 的插件 JAR 放入 Minecraft 服务端的 `plugins` 目录，启动一次生成配置，然后修改 `plugins/AstrBotRconBridge/config.yml`。下面列出需要关注的部分，其余配置保留生成的值：

```yaml
bridge:
  host: 127.0.0.1
  port: 25580
  token: "replace-with-your-own-token"
  read-timeout-ms: 15000

log-capture:
  enabled: true
  default-wait-ms: 1000
  max-wait-ms: 15000
  max-lines: 80
  file-path: "logs/latest.log"
```

将 `token` 换成自己的令牌，保存配置后重启 Minecraft 服务端。`file-path` 的相对路径以**服务端进程的工作目录**为基准；需要时可以填写绝对路径。

### 2. 安装 AstrBot 插件

在 AstrBot 管理面板的「插件」页面选择「安装插件」，通过 URL 安装 [本仓库](https://github.com/H-aaaa/astrbot_plugin_minecraftconsole)。面板操作可参考 [AstrBot 官方说明](https://docs.astrbot.app/use/webui.html#插件)。

手动安装时，将整个仓库放入 AstrBot 工作目录下的 `data/plugins/astrbot_plugin_minecraftconsole/`，确保 `main.py` 和 `metadata.yaml` 位于该目录第一层，然后在面板重载插件或重启 AstrBot。无需额外安装第三方 RCON 库。

### 3. 填写 AstrBot 插件配置

在插件配置页面填写管理员和连接信息。以下示例假设 AstrBot 与 Minecraft 运行在同一台机器、同一个网络环境中：

```json
{
  "enabled": true,
  "admins": ["123456789"],
  "rcon_host": "127.0.0.1",
  "rcon_port": 25580,
  "rcon_password": "replace-with-your-own-token",
  "timeout": 5,
  "max_attempts": 2,
  "test_on_first_use": true,
  "default_wait_ms": 1000,
  "max_output": 1500
}
```

把 `admins` 替换成实际聊天账号 ID，把 `rcon_password` 填成与桥接端 `bridge.token` 完全相同的值。保存后重载插件，使配置生效。

| AstrBot 配置 | 应填写的内容 |
| --- | --- |
| `rcon_host` | AstrBot 能访问到的 Minecraft 桥接服务地址 |
| `rcon_port` | 桥接端 `bridge.port`，默认 `25580` |
| `rcon_password` | 桥接端 `bridge.token` |

`bridge.host` 是服务端的**监听地址**。如果将它设为 `0.0.0.0`，AstrBot 的 `rcon_host` 应填写服务器实际 IP 或域名。

AstrBot 在 Docker 中运行时，`127.0.0.1` 指向 AstrBot 容器自身。跨容器或跨机器部署时，需要使用可达的地址，并配置相应的监听地址、端口映射和防火墙。桥接使用明文 TCP，适合通过本机、可信内网或加密隧道连接。

## 配置项

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `enabled` | `true` | 是否启用聊天命令 |
| `admins` | `[111, 222, 333]` | 面板中的示例管理员 ID，使用前替换为实际账号；支持数字或字符串 |
| `rcon_host` | `127.0.0.1` | 桥接服务地址 |
| `rcon_port` | `25580` | 桥接服务端口 |
| `rcon_password` | 空字符串 | 桥接 token，必填 |
| `timeout` | `5` | 连接、发送和网络等待余量，单位秒；命令回复会额外包含日志采集及服务端排队、调度时间 |
| `max_attempts` | `2` | 连接建立失败时的最大尝试次数，**包含首次**；设为 `1` 表示不重试 |
| `test_on_first_use` | `true` | 首次执行前发送 `PING` 检查桥接连接，不执行 Minecraft 命令；客户端重建后会重新检查 |
| `default_wait_ms` | `1000` | 未指定 `--t` 时请求的日志采集时间，单位毫秒 |
| `max_output` | `1500` | 聊天中保留的输出正文字符数，超出后追加截断提示；成功和失败正文都受此限制 |

管理员通过桥接端执行的是控制台命令，拥有相应的控制台权限。请使用自己的 token，并只在 `admins` 中填写需要此权限的账号。

## 执行命令与等待日志

```text
/mc-command <控制台命令> [--t=等待时间]
```

Minecraft 命令本体不带 `/`。例如发送 `/mc-command say hello`，桥接端实际执行 `say hello`。

```text
/mc-command list
/mc-command time set day
/mc-command weather clear
/mc-command lp editor --t=5s
/mc-command say hello --t=500ms
```

`--t` 是 AstrBot 插件的选项，会在转发前移除。建议放在命令末尾；支持以下整数格式：

| 写法 | 请求的采集时间 |
| --- | --- |
| `--t=5s` | 5 秒 |
| `--t=500ms` | 500 毫秒 |
| `--t=5` | 5 秒，省略单位时按秒处理 |
| `--t=0ms` | 不额外等待，可能错过尚未写入文件的日志 |
| 不写 `--t` | 使用 AstrBot 的 `default_wait_ms` |

额外等待时间从命令派发返回后计算，用于等待异步日志写入，**不会让命令再次执行**。桥接端会用 `log-capture.max-wait-ms` 限制实际等待时间，默认上限为 15 秒。

AstrBot 每次都会发送明确的等待值。因此，仅修改桥接端的 `log-capture.default-wait-ms`，不会覆盖 AstrBot 的 `default_wait_ms`。需要改变聊天命令的默认等待时间时，修改 AstrBot 侧配置。

## 回传结果与重试规则

桥接端在执行前记录日志位置，再返回采集窗口内新增的日志。输出保持日志顺序，不再依赖命令关键词过滤，也不再把 URL 提到前面。

- **正常回复**：显示执行的命令与输出正文。返回空字符串时显示 `(无输出)`。
- **服务端返回失败**：显示错误码和服务端返回的正文，便于查看命令报错、拒绝原因或超时信息。
- **尚未建立连接**：按 `max_attempts` 重试，此时命令还没有发送。
- **请求发送后超时、断连或响应异常**：不自动重发，提示先确认服务端执行状态。命令可能已执行，只是结果未完整送达。
- **认证失败、服务端明确返回失败、空输出**：均不会触发自动重发。

桥接端会串行处理请求及其采集窗口，但日志文件还可能包含玩家聊天、其他插件和异步任务的输出，因此返回内容不保证只属于当前命令。`✅ 已执行` 表示桥接端接受了命令，具体业务结果仍以返回内容和服务端状态为准。

桥接端默认最多返回 80 行，并限制日志读取量及正文长度；AstrBot 还会按 `max_output` 截断聊天输出。如果结果被截断，需要同时检查两端的限制。仅增大 `max_output` 无法恢复已经被桥接端截掉的部分。

## 常见问题

| 现象 | 排查方向 |
| --- | --- |
| 提示没有权限 | 确认 `admins` 包含当前聊天账号的 ID；不是群号或 Minecraft 玩家名 |
| 提示桥接未配置或认证失败 | 检查 `rcon_host`、`rcon_port`，并确认 `rcon_password` 与 `bridge.token` 一致 |
| 无法连接桥接服务 | 确认桥接插件已加载，端口是桥接端口，监听地址、容器网络和防火墙允许连接 |
| `FORBIDDEN_IP` | 检查桥接端 IP 白名单是否允许 AstrBot 的实际来源地址 |
| `(无输出)` | 确认桥接端 `log-capture.enabled: true`、日志路径正确；异步命令可适当增加 `--t`，并检查是否碰到服务端等待上限 |
| `Log read failed` | 检查桥接端日志文件路径和读取权限；这表示日志读取失败，命令可能已经执行 |
| `EXEC_REJECTED` | 查看返回正文，确认命令名称、参数及提供该命令的插件是否正确 |
| `EXEC_TIMEOUT` | 桥接端等待其他命令或服务端调度超时，先确认服务器状态及命令是否已执行 |
| 未能获取完整结果 | 检查 AstrBot 与 Minecraft 日志；请求发送后插件不会自动重发 |
| Folia 上某个插件命令报错 | 确认该插件和命令自身支持 Folia；桥接端的调度适配不能代替第三方插件的区域线程适配 |

## 升级到 1.3.1

- 修正日志等待时间与网络超时冲突的问题；例如 `--t=5s` 不会再直接撞上默认 5 秒网络超时。
- 限制自动重试为连接建立失败，避免命令已经执行后因丢失回复再次发送。
- 保留服务端失败回复中的错误码与正文，并提高单行响应读取上限以接收较长的 Base64 日志。
- 新配置的默认日志等待时间改为 `1000ms`。已有配置中的 `300ms` 等自定义值继续生效，需要时在面板手动调整。
- 将插件元数据与注册信息中的版本号统一为 `1.3.1`，配置字段名继续兼容原有桥接配置。

从早期原生 RCON 版本升级时，需要先安装桥接插件，再将旧的原生 RCON 端口和密码改成桥接端口与 token。新版桥接端只保留采集开关、等待时间、最大行数和文件路径；旧版关键词过滤、URL 排序等采集配置已不再使用。

## 问题反馈

请在 [Issues](https://github.com/H-aaaa/astrbot_plugin_minecraftconsole/issues) 中提供 AstrBot 版本、Minecraft 核心及版本、桥接版本、复现命令和相关错误日志。提交前删除 token、密码等敏感内容。
