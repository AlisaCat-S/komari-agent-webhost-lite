# komari-agent-webhost-lite

这是一个适用于 Komari 的 lite agent，适合不能方便运行主项目二进制 agent 的环境。当前已经兼容主项目的安装命令格式，你只需要把仓库地址替换成这个项目地址，就可以按主项目的习惯安装 lite 版。

安装脚本采用源码安装方式：会从本仓库下载 `py/komari-agent-python.py` 和 `py/requirements.txt`，在 `/opt/komari-lite` 下创建 Python 虚拟环境，安装依赖，并通过 `systemd` 启动 lite agent。

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
| `--install-ghproxy <url>` | 为 raw GitHub 源文件下载添加代理前缀 |
| `--include-nics <list>` | 只统计指定网卡，多个网卡用逗号分隔 |
| `--log-level <level>` | Agent 日志等级 |
| `--disable-web-ssh` | 兼容参数。lite agent 已移除远程控制功能 |
| `--enable-web-ssh` | 仅保留兼容性。lite agent 不提供远程控制功能 |

## 安装结果

安装脚本会创建以下内容：

- `/opt/komari-lite/py/komari-agent-python.py`
- `/opt/komari-lite/venv`
- `/etc/systemd/system/komari-agent-lite.service`

## Agent 运行参数

打包后的 lite agent 同时支持原始长参数和主项目兼容别名：

| 参数 | 说明 |
| --- | --- |
| `--http-server <url>` | Komari 服务端地址 |
| `-e`, `--endpoint <url>` | `--http-server` 的别名 |
| `--token <token>` | Komari token |
| `-t <token>` | `--token` 的别名 |
| `--interval <sec>` | 实时上报间隔 |
| `--reconnect-interval <sec>` | 重连间隔 |
| `--include-nics <list>` | 只统计指定网卡 |
| `--disable-web-ssh` | 兼容参数。lite agent 已移除远程控制功能 |
| `--enable-web-ssh` | 仅保留兼容性。lite agent 不提供远程控制功能 |

## 远程控制状态

lite agent 不包含远程执行和终端控制功能。

- 收到控制事件后会直接拒绝执行。
- `--disable-web-ssh`、`--enable-web-ssh`、`KOMARI_DISABLE_REMOTE_CONTROL` 仅用于兼容主项目风格命令和旧配置。

## 环境变量

- `KOMARI_HTTP_SERVER`
- `KOMARI_TOKEN`
- `KOMARI_INTERVAL`
- `KOMARI_RECONNECT_INTERVAL`
- `KOMARI_LOG_LEVEL`
- `KOMARI_DISABLE_REMOTE_CONTROL`
- `KOMARI_INCLUDE_NICS`
