# AstrBot Minecraft Console 插件

通过聊天指令将 Minecraft 控制台命令发送到 **Minecraft 服务端桥接插件** 执行，并将命令返回、日志输出或错误信息回显到聊天中。

本版本 **不再使用原生 RCON 协议**，而是连接 Minecraft 服务端上的桥接插件：

**桥接插件项目：** AstrBotRconBridge  
`https://github.com/H-aaaa/AstrBotRconBridge`

> [!WARNING]
> 本插件及文档由 AI 协助整理，内容仅供参考，请结合实际环境测试后使用。
>
> 已测试：
> - Spigot 1.8.8
> - Spigot 1.21.11
>
> 插件目前仍处于开发阶段，无法 100% 保证在所有服务端核心、插件组合和命令场景下都完全一致。
>
> 如有问题请提交 issue 或联系作者。

---

## ✨ 功能特性

- ✅ `/mc-command <命令>`：在聊天中执行 Minecraft 控制台命令
- ✅ 管理员校验：仅允许 `admins` 列表中的用户使用
- ✅ 基于桥接插件通信：不再依赖原生 RCON 回包限制
- ✅ 支持等待日志输出窗口：适合 `lp editor` 等延迟返回命令
- ✅ 默认只执行一次命令：不会因为“无输出”而重复执行
- ✅ 网络异常自动重试：最多重试 `max_attempts` 次
- ✅ 输出截断：防止过长日志刷屏
- ✅ 支持错误回显：如参数错误、命令报错、插件返回失败等

---

## 🧭 工作原理

AstrBot 插件本身不直接使用 Minecraft 原生 RCON 协议，而是连接服务端上的 **AstrBotRconBridge** 插件。

执行流程如下：

1. 聊天中发送 `/mc-command <命令>`
2. AstrBot 插件解析命令和可选参数 `--t=...`
3. AstrBot 连接 Minecraft 服务端桥接插件
4. 桥接插件在服务端内执行控制台命令
5. 桥接插件收集：
   - 命令同步返回
   - 等待窗口内的日志输出
   - 可能的错误信息
6. AstrBot 将结果回显到聊天中

---

## 🔁 配置映射

AstrBot 侧保留原有配置字段名，但其含义已经映射到桥接插件：

| AstrBot 配置项 | 对应桥接插件配置 |
|---|---|
| `rcon_host` | `bridge.host` |
| `rcon_port` | `bridge.port` |
| `rcon_password` | `bridge.token` |

也就是说：

- `rcon_host` 不再是原生 RCON 地址，而是 **桥接插件监听地址**
- `rcon_port` 不再是原生 RCON 端口，而是 **桥接插件监听端口**
- `rcon_password` 不再是原生 RCON 密码，而是 **桥接插件 token**

---

## 🚀 指令示例

```text
/mc-command list
/mc-command say hello
/mc-command time set day
/mc-command lp editor --t=5s
/mc-command say hello --t=500ms
```

### `--t=...` 的作用

`--t=...` 用于指定一个**日志等待窗口**，适合那些不会立刻返回结果、而是过一会儿才输出日志的命令。

例如：

```text
/mc-command lp editor --t=5s
```

表示：

- 执行 `lp editor`
- 再额外等待 5 秒
- 将这段时间内相关的日志输出一起回显

支持格式：

- `--t=5s`
- `--t=500ms`

---

## 📌 行为说明

### 1. 默认只执行一次
插件默认只发送一次命令，不会因为“无输出”而再次执行命令。

### 2. 网络错误可重试
若出现连接失败、超时、桥接插件暂不可用等网络层错误，会最多重试 `max_attempts` 次。

### 3. `--t=...` 只影响等待窗口
`--t=...` 不会重复执行命令，只会决定执行后等待日志输出的时间。

### 4. 输出可能来自两部分
桥接插件最终返回的内容可能来自：

- 命令同步返回
- 等待窗口内的日志输出
- 服务端错误信息

### 5. 部分命令回显依赖日志
某些插件命令或异步命令不会立即回包，而是通过控制台日志输出结果，例如：

- `lp editor`
- 某些管理插件命令
- 某些异步执行的插件命令

此时建议使用 `--t=...`。

---

## 📦 安装

### 方式一：手动安装

将插件文件夹放入 AstrBot 插件目录，例如：

- Windows：`C:\Users\<你>\.astrbot\data\plugins\astrbot_plugin_minecraftconsole`
- Linux：`~/.astrbot/data/plugins/astrbot_plugin_minecraftconsole`

确保插件目录中至少包含以下文件：

```text
astrbot_plugin_minecraftconsole/
  __init__.py
  main.py
  config.py
  rcon_client.py
  utils.py
  message_formatter.py
  _conf_schema.json
```

然后重启 AstrBot 或在面板中重新加载插件。

### 方式二：通过 AstrBot 客户端远程安装

按 AstrBot 客户端插件安装流程完成安装即可。

---

## ⚙️ 配置说明

本插件使用 AstrBot 的插件配置系统（`_conf_schema.json`）自动生成配置项并自动保存。

在 AstrBot 管理面板中找到本插件配置并填写：

| 配置项 | 类型 | 默认值 | 说明 |
|---|---|---:|---|
| `enabled` | bool | `true` | 是否启用插件 |
| `admins` | list | `[111, 222, 333]` | 允许使用 `/mc-command` 的管理员 user_id 列表 |
| `rcon_host` | string | `127.0.0.1` | 桥接插件监听地址 |
| `rcon_port` | int | `25580` | 桥接插件监听端口 |
| `rcon_password` | string | `""` | 桥接插件 token |
| `timeout` | float | `5` | 网络超时时间（秒） |
| `max_output` | int | `1500` | 聊天回显最大长度 |
| `max_attempts` | int | `2` | 网络失败最大重试次数 |
| `default_wait_ms` | int | `300` | 默认日志等待时间（毫秒） |
| `empty_output_wait_ms` | int | `0` | 保留兼容项，建议为 `0`，避免重复执行 |

### ✅ `admins` 示例

```yaml
admins:
  - 111
  - 222
  - 333
```

说明：

- `admins` 支持数字或字符串
- 最终只要能匹配 `event.get_sender_id()` 的值即可

---

## 🧩 Minecraft 服务端要求

### 必须安装桥接插件

本插件依赖 Minecraft 服务端安装 **AstrBotRconBridge**。

请先在 Minecraft 服务端安装并配置桥接插件，再配置 AstrBot 侧连接信息。

### 桥接插件示例配置

```yaml
bridge:
  host: 127.0.0.1
  port: 25580
  token: "change_me"
  read-timeout-ms: 15000

log-capture:
  enabled: true
  default-wait-ms: 300
  max-wait-ms: 15000
  max-lines: 80
  only-when-empty: false
  include-console-executor-line: false
  regex-filter: ""
  url-first: true
  file-path: "logs/latest.log"
  level-mode: "INFO_ONLY"
  related-only: false
  include-url-lines: true
  extra-keywords:
    - "luckperms"
    - "lp"
    - "editor"
    - "uuid"
    - "invalid format"

security:
  enable-ip-whitelist: false
  whitelist:
    - "127.0.0.1"
    - "::1"

messages:
  auth-failed: "AUTH_FAILED"
  forbidden-ip: "FORBIDDEN_IP"
  bad-request: "BAD_REQUEST"
  internal-error: "INTERNAL_ERROR"
```

---

## 🌐 网络说明

若 AstrBot 和 Minecraft 服务端不在同一台机器，请注意：

- 放行桥接插件监听端口
- 配置正确的 `bridge.host`
- 云服务器需放行安全组端口
- Docker / 面板服需确认端口映射正常

如果只在本机使用，建议：

```yaml
bridge:
  host: 127.0.0.1
```

这样更安全。

---

## 🚫 命令使用注意事项

### 1. 不要带斜杠
你发送给插件的参数应当是 **控制台命令本体**：

- ✅ 正确：`/mc-command say hello`
- ❌ 错误：`/mc-command /say hello`

### 2. 某些命令需要等待日志
例如：

```text
/mc-command lp editor --t=5s
```

如果不加等待窗口，可能会拿不到异步输出。

### 3. 某些错误信息来自日志
有些命令不会同步返回失败，而是把错误打印到控制台日志中。桥接插件会尝试把这些错误回显给 AstrBot。

---

## 🛠️ 常见问题（FAQ）

### 1）提示“你没有权限使用该指令”
检查 AstrBot 面板配置里的 `admins` 是否包含你的 `user_id`。

### 2）提示“桥接未配置”或认证失败
检查：

- `rcon_host` 是否正确
- `rcon_port` 是否正确
- `rcon_password` 是否与桥接插件 `bridge.token` 一致
- Minecraft 服务端桥接插件是否已启动

### 3）执行命令后显示“无输出”
可能原因：

- 该命令本身没有同步返回
- 命令结果通过日志异步输出
- 等待窗口不足
- 桥接插件日志过滤未命中

建议：

- 给命令加 `--t=...`
- 检查桥接插件 `log-capture` 配置
- 检查 `file-path` 是否正确指向 `logs/latest.log`

例如：

```text
/mc-command lp editor --t=5s
```

### 4）执行成功，但错误信息没回显
可能是桥接插件开启了过严的日志过滤，例如：

```yaml
related-only: true
```

某些错误日志中不包含原命令关键词，会被过滤掉。  
建议先改为：

```yaml
related-only: false
```

### 5）执行命令卡住/超时
可能原因：

- `rcon_host` / `rcon_port` 配置错误
- 端口未放行
- `timeout` 太小
- 桥接插件未正常启动
- 桥接插件等待日志时间过长

### 6）为什么 `lp editor` 这类命令需要 `--t=...`
因为这类命令通常不是立刻把结果同步返回，而是稍后输出一条日志或链接。  
所以需要通过等待窗口把异步日志一并捕获回来。

### 7）为什么不是原生 RCON
因为原生 RCON 在很多命令场景下无法稳定拿到完整输出，尤其是：

- 插件命令
- 异步命令
- 仅写入日志的命令
- 某些报错信息

桥接插件可以更灵活地收集：

- 同步命令返回
- 服务端日志
- 错误信息

因此整体表现比原生 RCON 更稳定。

---

## 🔒 安全建议

- 强烈建议不要在公开群聊中暴露此功能
- 将 `admins` 设置为最小范围
- 为桥接插件设置强随机 `token`
- 如有需要，在桥接插件侧开启 IP 白名单
- 如担心误操作，可自行加入命令黑名单 / 白名单（如禁止 `stop`、`op` 等）

---

## 📣 说明

本插件仍在持续调整中，不同 Minecraft 版本、核心和插件组合下，输出表现可能略有差异。  
如遇问题，请结合控制台日志、桥接插件配置与 AstrBot 配置一并排查。
