# komari-agent-webhost-lite

Lite agent for Komari deployments where running the main binary agent is inconvenient. This project now supports the main project installer command style, so you can replace only the repository URL and keep the same installation habit. The installer performs a source-based install: it downloads `py/komari-agent-python.py` and `py/requirements.txt` from this repository, creates a Python virtual environment under `/opt/komari-lite`, installs dependencies, and runs the lite agent with systemd.

## Install

Main project compatible example:

```bash
wget -qO- https://ghfast.top/raw.githubusercontent.com/AlisaCat-S/komari-agent-webhost-lite/refs/heads/main/install.sh | sudo bash -s -- -e https://example.com -t TokenXXXXXXXXXXXX --install-ghproxy https://ghfast.top --include-nics eth0
```

Legacy two-argument install is still supported:

```bash
sudo bash install.sh https://example.com TokenXXXXXXXXXXXX
```

## Installer options

| Option | Description |
| --- | --- |
| `-e`, `--endpoint`, `--http-server <url>` | Komari server address |
| `-t`, `--token <token>` | Komari token |
| `--install-ghproxy <url>` | Prefix raw GitHub source downloads with a proxy |
| `--include-nics <list>` | Restrict network statistics to specific NICs, separated by commas |
| `--log-level <level>` | Agent log level |
| `--disable-web-ssh` | Compatibility flag. Remote control is already removed in lite agent |
| `--enable-web-ssh` | Compatibility flag only. Lite agent does not provide remote control support |

## Installation result

The installer creates:

- `/opt/komari-lite/py/komari-agent-python.py`
- `/opt/komari-lite/venv`
- `/etc/systemd/system/komari-agent-lite.service`

## Agent runtime options

The packaged agent accepts both the original long options and the main-project compatible aliases:

| Option | Description |
| --- | --- |
| `--http-server <url>` | Komari server address |
| `-e`, `--endpoint <url>` | Alias of `--http-server` |
| `--token <token>` | Komari token |
| `-t <token>` | Alias of `--token` |
| `--interval <sec>` | Realtime report interval |
| `--reconnect-interval <sec>` | Reconnect interval |
| `--include-nics <list>` | Restrict network statistics to selected NICs |
| `--disable-web-ssh` | Compatibility flag. Remote control is already removed in lite agent |
| `--enable-web-ssh` | Compatibility flag only. Lite agent does not provide remote control support |

## Remote control status

Lite agent does not include remote execution or terminal control support.

- Incoming control events are rejected.
- `--disable-web-ssh`, `--enable-web-ssh`, and `KOMARI_DISABLE_REMOTE_CONTROL` are kept only for compatibility with main-project style commands and old configs.

## Environment variables

- `KOMARI_HTTP_SERVER`
- `KOMARI_TOKEN`
- `KOMARI_INTERVAL`
- `KOMARI_RECONNECT_INTERVAL`
- `KOMARI_LOG_LEVEL`
- `KOMARI_DISABLE_REMOTE_CONTROL`
- `KOMARI_INCLUDE_NICS`
