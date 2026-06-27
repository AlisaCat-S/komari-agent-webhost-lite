# komari-agent-webhost-lite

这是一个适用于 Komari 的 lite agent，适合不方便运行主项目二进制 agent 的环境。

当前已经兼容主项目的安装命令格式，你只需要把仓库地址替换成这个项目地址，就可以按主项目的习惯安装 lite 版本。

安装脚本采用源码安装方式：会从本仓库下载 `py/komari-agent-python.py` 和 `py/requirements.txt`，在 `/opt/komari-lite` 下创建 Python 虚拟环境，安装依赖，并通过 `systemd` 启动 lite agent。

`pip` 依赖安装会自动在常见国内镜像和官方源之间回退切换；如果你要强制指定源，也可以提前设置 `PIP_INDEX_URL`。

## 安装

兼容主项目格式的安装示例：

```bash
wget -qO- https://ghfast.top/raw.githubusercontent.com/AlisaCat-S/komari-agent-webhost-lite/refs/heads/main/install.sh | sudo bash -s -- -e https://example.com -t TokenXXXXXXXXXXXX --install-ghproxy https://ghfast.top --include-nics eth0
```

旧的双参数安装方式仍然可用：

```bash
sudo bash install.sh https://example.com TokenXXXXXXXXXXXX
```

## 安装脚本参数

| 参数 | 说明 |
| --- | --- |
| `-e`, `--endpoint`, `--http-server <url>` | Komari 服务端地址 |
| `-t`, `--token <token>` | Komari token |
| `--install-ghproxy <url>` | 为 GitHub raw 下载添加代理前缀 |
| `--include-nics <list>` | 只统计指定网卡，多个网卡用逗号分隔 |
| `--log-level <level>` | Agent 日志等级，默认值为 `1` |
| `--disable-web-ssh` | 兼容参数，保持禁用远程控制 |
| `--enable-web-ssh` | 兼容参数，仅保留命令行兼容性，lite agent 实际不提供远程控制 |

## 安装结果

安装脚本会创建以下内容：

- `/opt/komari-lite/py/komari-agent-python.py`
- `/opt/komari-lite/requirements.txt`
- `/opt/komari-lite/venv`
- `/etc/systemd/system/komari-agent-lite.service`

## Agent 运行参数

lite agent 支持以下运行参数：

| 参数 | 说明 |
| --- | --- |
| `--http-server <url>` | Komari 服务端地址 |
| `-e`, `--endpoint <url>` | `--http-server` 的兼容别名 |
| `--token <token>` | Komari token |
| `-t <token>` | `--token` 的兼容别名 |
| `--interval <sec>` | 实时上报间隔 |
| `--reconnect-interval <sec>` | 重连间隔 |
| `--include-nics <list>` | 只统计指定网卡，多个网卡用逗号分隔 |
| `--log-level <level>` | 日志等级 |
| `--disable-web-ssh` | 兼容参数，启用“禁用远程控制”标记 |
| `--enable-web-ssh` | 兼容参数，仅用于兼容旧参数风格 |

## 远程控制状态

lite agent 不包含远程执行和终端控制功能。

- 收到控制事件后会直接拒绝执行。
- `--disable-web-ssh`、`--enable-web-ssh`、`KOMARI_DISABLE_REMOTE_CONTROL` 仅用于兼容主项目命令风格和旧配置。

## 环境变量

- `KOMARI_HTTP_SERVER`
- `KOMARI_TOKEN`
- `KOMARI_INTERVAL`
- `KOMARI_RECONNECT_INTERVAL`
- `KOMARI_LOG_LEVEL`
- `KOMARI_DISABLE_REMOTE_CONTROL`
- `KOMARI_INCLUDE_NICS`
