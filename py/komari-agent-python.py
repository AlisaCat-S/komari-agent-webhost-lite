#!/usr/bin/env python3

#
# komari-agent-python by liming2038
# This fork keeps the lightweight monitoring client behavior and strips
# remote control execution. Treat users and operators as peers.
#

import asyncio
import json
import os
import platform
import sys
import time
import subprocess
import socket
import aiohttp
import websockets
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any

if platform.system() != "Windows":
    import pty
    import select
else:
    pty = None
    select = None


class Logger:
    """Simple logger."""

    _log_level = 0  # 0=off, 1=basic, 2=websocket, 3=terminal, 4=network, 5=disk

    @classmethod
    def set_log_level(cls, level: int):
        """Set the current log level."""
        cls._log_level = level

    @classmethod
    def _log(cls, message: str, level: str = "INFO"):
        """Emit a log line."""
        if cls._log_level == 0 and level != "ERROR":
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)

        if level == "ERROR":
            print(log_message, file=sys.stderr)

    @classmethod
    def debug(cls, message: str, debug_level: int = 1):
        """Emit a debug log when the exact level matches."""
        if cls._log_level == debug_level:
            cls._log(message, "DEBUG")

    @classmethod
    def info(cls, message: str):
        """Emit an info log."""
        cls._log(message, "INFO")

    @classmethod
    def warning(cls, message: str):
        """Emit a warning log."""
        cls._log(message, "WARNING")

    @classmethod
    def error(cls, message: str):
        """Emit an error log."""
        cls._log(message, "ERROR")


class SystemInfoCollector:
    """Collect basic and realtime system information."""

    VERSION = "komari-agent-python-1.0.0"

    def __init__(self, include_nics: Optional[List[str]] = None):
        self.last_network_stats = {"rx": 0, "tx": 0}
        self.total_network_up = 0
        self.total_network_down = 0
        self.last_network_time = time.time()
        self._cpu_initialized = False
        self._cpu_init_lock = asyncio.Lock()
        self.include_nics = set(include_nics or [])

    async def get_basic_info(self) -> Dict[str, Any]:
        """Collect basic system metadata."""
        dist_info = self._get_linux_distribution()

        ipv4, ipv6 = await asyncio.gather(
            self._get_public_ip_v4(),
            self._get_public_ip_v6(),
            return_exceptions=True,
        )

        ipv4 = ipv4 if not isinstance(ipv4, Exception) else None
        ipv6 = ipv6 if not isinstance(ipv6, Exception) else None

        if isinstance(ipv4, Exception):
            Logger.debug(f"Failed to get IPv4: {ipv4}", 1)
            ipv4 = None
        if isinstance(ipv6, Exception):
            Logger.debug(f"Failed to get IPv6: {ipv6}", 1)
            ipv6 = None

        os_name = (
            f"{dist_info['name']} {dist_info['version']}"
            if dist_info["name"] != "Unknown"
            else platform.system()
        )

        info = {
            "arch": platform.machine(),
            "cpu_cores": psutil.cpu_count(),
            "cpu_name": self._get_cpu_name(),
            "disk_total": await self._get_disk_total(),
            "gpu_name": "",
            "ipv4": ipv4,
            "ipv6": ipv6,
            "mem_total": psutil.virtual_memory().total,
            "os": os_name,
            "kernel_version": platform.release(),
            "swap_total": psutil.swap_memory().total,
            "version": self.VERSION,
            "virtualization": self._get_virtualization(),
        }

        Logger.debug(f"Basic info payload: {json.dumps(info, indent=2)}", 1)
        return info

    async def get_realtime_info(self) -> Dict[str, Any]:
        """Collect realtime monitoring data."""
        cpu_usage = await self._get_cpu_usage()
        network_stats = await self._get_network_stats()
        memory_info = await self._get_memory_info()
        disk_info = await self._get_disk_info()

        info = {
            "cpu": {
                "usage": cpu_usage
            },
            "ram": {
                "total": memory_info["ram_total"],
                "used": memory_info["ram_used"],
            },
            "swap": {
                "total": memory_info["swap_total"],
                "used": memory_info["swap_used"],
            },
            "load": {
                "load1": round(psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") and psutil.getloadavg() else 0, 2),
                "load5": round(psutil.getloadavg()[1] if hasattr(psutil, "getloadavg") and psutil.getloadavg() else 0, 2),
                "load15": round(psutil.getloadavg()[2] if hasattr(psutil, "getloadavg") and psutil.getloadavg() else 0, 2),
            },
            "disk": {
                "total": disk_info["total"],
                "used": disk_info["used"],
            },
            "network": {
                "up": network_stats["up"],
                "down": network_stats["down"],
                "totalUp": network_stats["total_up"],
                "totalDown": network_stats["total_down"],
            },
            "connections": {
                "tcp": await self._get_tcp_connections(),
                "udp": await self._get_udp_connections(),
            },
            "uptime": int(time.time() - psutil.boot_time()),
            "process": len(psutil.pids()),
            "message": "",
        }

        Logger.debug(f"Realtime info payload: {json.dumps(info, indent=2)}", 2)
        return info

    def _get_cpu_name(self) -> str:
        """Return a best-effort CPU model name."""
        try:
            if platform.system() == "Windows":
                import winreg

                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
                )
                cpu_name = winreg.QueryValueEx(key, "ProcessorNameString")[0]
                winreg.CloseKey(key)
                return cpu_name.strip()
            else:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if line.strip().startswith("model name"):
                            return line.split(":")[1].strip()
        except Exception as e:
            Logger.debug(f"Failed to get CPU name: {e}", 1)

        return "Unknown CPU"

    async def _get_cpu_usage(self) -> float:
        """Return CPU usage without repeated blocking warmup."""
        async with self._cpu_init_lock:
            if not self._cpu_initialized:
                psutil.cpu_percent(interval=0.1)
                self._cpu_initialized = True
                return 0.0

        try:
            usage = psutil.cpu_percent(interval=None)
            return round(max(0, min(100, usage)), 2)
        except Exception as e:
            Logger.debug(f"Failed to get CPU usage: {e}", 2)
            return 0.0

    async def _get_memory_info(self) -> Dict[str, int]:
        """Return memory totals in bytes."""
        try:
            virtual_memory = psutil.virtual_memory()
            swap_memory = psutil.swap_memory()

            return {
                "ram_total": virtual_memory.total,
                "ram_used": virtual_memory.used,
                "swap_total": swap_memory.total,
                "swap_used": swap_memory.used,
            }
        except Exception as e:
            Logger.debug(f"Failed to get memory info: {e}", 2)
            return {
                "ram_total": 0,
                "ram_used": 0,
                "swap_total": 0,
                "swap_used": 0,
            }

    def _get_physical_disk_device(self, device_path: str) -> Optional[str]:
        if platform.system() != "Linux":
            return device_path

        import re

        dev_name = device_path.replace("/dev/", "")
        if not dev_name:
            return None

        device_patterns = [
            r"^(md[0-9]+)$",
            r"^(sd[a-z]+)\d*$",
            r"^(vd[a-z]+)\d*$",
            r"^(xvd[a-z]+)\d*$",
            r"^(mmcblk\d+)p?\d*$",
            r"^(nvme\d+n\d+)p?\d*$",
        ]
        for pattern in device_patterns:
            match = re.match(pattern, dev_name)
            if match:
                return f"/dev/{match.group(1)}"

        if not re.search(r"\d", dev_name):
            return device_path

        sys_block_path = f"/sys/block/{dev_name}"
        if os.path.exists(sys_block_path):
            real_parent = os.path.realpath(os.path.dirname(sys_block_path))
            real_path = os.path.realpath(sys_block_path)
            if not os.path.isdir(real_path):
                real_grandparent = os.path.dirname(real_parent)
                if real_grandparent.endswith("/sys/block"):
                    physical_name = os.path.basename(real_parent)
                    if self._is_physical_disk(f"/dev/{physical_name}"):
                        return f"/dev/{physical_name}"

        return None

    async def _get_disk_info(self) -> Dict[str, int]:
        try:
            total_bytes = 0
            used_bytes = 0
            seen_physical_devices = set()

            partitions = psutil.disk_partitions()
            Logger.debug(f"Found {len(partitions)} partitions", 5)
            for partition in partitions:
                device = partition.device
                mountpoint = partition.mountpoint
                fstype = partition.fstype

                if fstype in {
                    "tmpfs",
                    "devtmpfs",
                    "overlay",
                    "squashfs",
                    "proc",
                    "sysfs",
                    "debugfs",
                    "configfs",
                    "cgroup",
                    "cgroup2",
                    "pstore",
                    "bpf",
                    "tracefs",
                    "securityfs",
                    "efivarfs",
                }:
                    Logger.debug(
                        f"Skipping virtual filesystem: {fstype} "
                        f"(device: {device}, mountpoint: {mountpoint})",
                        5,
                    )
                    continue

                physical_device = self._get_physical_disk_device(device)
                if not physical_device:
                    Logger.debug(
                        f"Could not resolve physical disk for partition: {device} "
                        f"(mountpoint: {mountpoint})",
                        5,
                    )
                    continue

                if physical_device in seen_physical_devices:
                    Logger.debug(
                        f"Physical disk already counted: {physical_device} "
                        f"(partition: {device}, mountpoint: {mountpoint})",
                        5,
                    )
                    continue

                if not self._is_physical_disk(physical_device):
                    Logger.debug(
                        f"Skipping non-physical disk {physical_device} "
                        f"(from partition {device})",
                        5,
                    )
                    continue

                try:
                    usage = psutil.disk_usage(mountpoint)
                    Logger.debug(
                        f"Counting physical disk {physical_device} from {device}: "
                        f"mountpoint={mountpoint}, total={usage.total} bytes, "
                        f"used={usage.used} bytes, free={usage.free} bytes, "
                        f"usage={usage.percent:.2f}%",
                        5,
                    )
                    total_bytes += usage.total
                    used_bytes += usage.used
                    Logger.debug(
                        f"Current disk totals: total={total_bytes} bytes, "
                        f"used={used_bytes} bytes",
                        5,
                    )
                    seen_physical_devices.add(physical_device)
                except (PermissionError, OSError) as e:
                    Logger.debug(
                        f"Skipping partition {device} (mountpoint: {mountpoint}, "
                        f"physical disk: {physical_device}): {e}",
                        5,
                    )
                    continue

            Logger.debug(
                f"Disk statistics complete after dedupe: total={total_bytes} bytes, "
                f"used={used_bytes} bytes",
                5,
            )
            return {
                "total": total_bytes,
                "used": used_bytes,
            }
        except Exception as e:
            Logger.debug(f"Failed to get disk info: {e}", 5)
            return {"total": 0, "used": 0}

    async def _get_disk_total(self) -> int:
        """Return total disk capacity."""
        disk_info = await self._get_disk_info()
        return disk_info["total"]

    def _is_physical_disk(self, device: str) -> bool:
        if platform.system() == "Windows":
            return any(device.lower().startswith(drive) for drive in ["c:", "d:", "e:", "f:", "g:", "h:"])
        else:
            import re

            physical_patterns = [
                r"^/dev/sd[a-z]+$",
                r"^/dev/vd[a-z]+$",
                r"^/dev/xvd[a-z]+$",
                r"^/dev/nvme[0-9]+n[0-9]+$",
                r"^/dev/mmcblk[0-9]+$",
                r"^/dev/md[0-9]+$",
                r"^zroot/.*$",
            ]
            is_physical_device = any(re.match(pattern, device) for pattern in physical_patterns)
            return is_physical_device

    async def _get_network_stats(self) -> Dict[str, int]:
        """
        Return aggregated physical NIC traffic statistics.

        Virtual interfaces are excluded.
        """
        try:
            net_io = psutil.net_io_counters(pernic=True)
            current_time = time.time()

            total_current_rx = 0
            total_current_tx = 0

            exclude_patterns = ["lo", "docker", "veth", "br-", "tun", "virbr"]

            for interface, stats in net_io.items():
                if self.include_nics and interface not in self.include_nics:
                    Logger.debug(f"Skipping NIC not listed in include_nics: {interface}", 4)
                    continue
                if any(pattern in interface for pattern in exclude_patterns):
                    Logger.debug(f"Skipping virtual NIC: {interface}", 4)
                    continue

                Logger.debug(
                    f"Counting physical NIC {interface}: "
                    f"RX={stats.bytes_recv}, TX={stats.bytes_sent}",
                    4,
                )
                total_current_rx += stats.bytes_recv
                total_current_tx += stats.bytes_sent

            if self.last_network_stats["rx"] == 0:
                Logger.debug(
                    f"Initializing network counters: "
                    f"download={total_current_rx}, upload={total_current_tx}",
                    4,
                )
                self.total_network_down = total_current_rx
                self.total_network_up = total_current_tx
                self.last_network_stats = {"rx": total_current_rx, "tx": total_current_tx}
                self.last_network_time = current_time

                return {
                    "up": 0,
                    "down": 0,
                    "total_up": self.total_network_up,
                    "total_down": self.total_network_down,
                }

            down_speed = 0.0
            up_speed = 0.0
            time_diff = current_time - self.last_network_time
            if time_diff > 0:
                down_speed = (total_current_rx - self.last_network_stats["rx"]) / time_diff
                up_speed = (total_current_tx - self.last_network_stats["tx"]) / time_diff

                down_speed = max(0, down_speed)
                up_speed = max(0, up_speed)

                self.total_network_down = total_current_rx
                self.total_network_up = total_current_tx

                Logger.debug(
                    f"Network stats: down={int(down_speed)} B/s, up={int(up_speed)} B/s, "
                    f"total_down={self.total_network_down}, total_up={self.total_network_up}",
                    4,
                )

            self.last_network_stats = {"rx": total_current_rx, "tx": total_current_tx}
            self.last_network_time = current_time

            return {
                "up": int(up_speed),
                "down": int(down_speed),
                "total_up": self.total_network_up,
                "total_down": self.total_network_down,
            }

        except Exception as e:
            Logger.debug(f"Failed to collect per-NIC network stats: {e}", 4)
            return {"up": 0, "down": 0, "total_up": 0, "total_down": 0}

    async def _get_tcp_connections(self) -> int:
        """Return TCP connection count."""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["netstat", "-n", "-p", "tcp"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                count = len([line for line in result.stdout.split("\n") if "ESTABLISHED" in line])
                return count
            else:
                connections = psutil.net_connections(kind="tcp")
                return len([conn for conn in connections if conn.status == "ESTABLISHED"])
        except Exception as e:
            Logger.debug(f"Failed to get TCP connection count: {e}", 2)
            return 0

    async def _get_udp_connections(self) -> int:
        """Return UDP connection count."""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["netstat", "-n", "-p", "udp"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                count = len([line for line in result.stdout.split("\n") if "UDP" in line and line.strip()])
                return count
            else:
                connections = psutil.net_connections(kind="udp")
                return len(connections)
        except Exception as e:
            Logger.debug(f"Failed to get UDP connection count: {e}", 2)
            return 0

    def _get_linux_distribution(self) -> Dict[str, str]:
        """Return Linux distribution info when available."""
        try:
            if platform.system() == "Linux":
                if os.path.exists("/etc/os-release"):
                    with open("/etc/os-release", "r") as f:
                        content = f.read()

                    name = "Unknown"
                    version = "Unknown"

                    for line in content.split("\n"):
                        if line.startswith("ID="):
                            name = line.replace("ID=", "").replace('"', "").strip()
                        elif line.startswith("VERSION_ID="):
                            version = line.replace("VERSION_ID=", "").replace('"', "").strip()

                    return {"name": name, "version": version}
        except Exception:
            pass

        return {"name": "Unknown", "version": "Unknown"}

    def _get_virtualization(self) -> str:
        """Return best-effort virtualization type."""
        try:
            if platform.system() == "Linux":
                if os.path.exists("/.dockerenv"):
                    return "Docker"

                if os.path.exists("/proc/1/cgroup"):
                    with open("/proc/1/cgroup", "r") as f:
                        content = f.read()
                        if "docker" in content:
                            return "Docker"
                        elif "lxc" in content:
                            return "LXC"

                if os.path.exists("/proc/cpuinfo"):
                    with open("/proc/cpuinfo", "r") as f:
                        content = f.read()
                        if "QEMU" in content or "KVM" in content:
                            return "QEMU"
        except Exception:
            pass

        return "None"

    async def _get_public_ip_v4(self) -> Optional[str]:
        """Return public IPv4 when available."""
        services = [
            "https://api.ipify.org",
            "https://icanhazip.com",
            "https://checkip.amazonaws.com",
            "https://ifconfig.me/ip",
        ]

        for service in services:
            try:
                ip = await self._fetch_ip(service)
                if ip and self._is_valid_ipv4(ip):
                    return ip
            except Exception:
                continue

        return None

    async def _get_public_ip_v6(self) -> Optional[str]:
        """Return public IPv6 when available."""
        services = [
            "https://api6.ipify.org",
            "https://icanhazip.com",
        ]

        for service in services:
            try:
                ip = await self._fetch_ip(service)
                if ip and self._is_valid_ipv6(ip):
                    return ip
            except Exception:
                continue

        return None

    async def _fetch_ip(self, url: str) -> str:
        """Fetch plain-text IP data from a service."""
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers={"User-Agent": self.VERSION}) as response:
                if response.status == 200:
                    return (await response.text()).strip()
                else:
                    raise Exception(f"HTTP {response.status}")

    def _is_valid_ipv4(self, ip: str) -> bool:
        """Validate an IPv4 string."""
        try:
            socket.inet_pton(socket.AF_INET, ip)
            return True
        except socket.error:
            return False

    def _is_valid_ipv6(self, ip: str) -> bool:
        """Validate an IPv6 string."""
        try:
            socket.inet_pton(socket.AF_INET6, ip)
            return True
        except socket.error:
            return False


class EventHandler:
    """Handle events sent by the server."""

    def __init__(self, config: Dict[str, Any], disable_remote_control: bool = False):
        self.config = config
        self.disable_remote_control = disable_remote_control

    async def handle_event(self, event: Dict[str, Any]):
        """Log and reject remote-control style events."""
        message_type = event.get("message", "")

        Logger.info(f"Received server event: {message_type}")
        Logger.info(f"Event payload: {json.dumps(event, indent=2)}")
        Logger.info("Execution rejected")


class KomariMonitorClient:
    """Main monitoring client."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.disable_remote_control = config.get("disable_remote_control", False)
        self.system_info = SystemInfoCollector(config.get("include_nics"))
        self.event_handler = EventHandler(config, self.disable_remote_control)
        self.last_basic_info_report = 0
        self.BASIC_INFO_INTERVAL = 300

    async def run(self):
        """Run the monitoring client forever."""
        Logger.info("Starting Komari monitor client (Python edition)")
        if self.disable_remote_control:
            Logger.info("Remote control support is disabled")

        while True:
            try:
                await self._run_monitoring_cycle()
                await asyncio.sleep(self.config.get("reconnect_interval", 5))
            except Exception as e:
                Logger.error(f"Monitoring cycle failed: {e}")
                Logger.info(f"Retrying in {self.config.get('reconnect_interval', 5)} seconds...")
                await asyncio.sleep(self.config.get("reconnect_interval", 5))

    async def _run_monitoring_cycle(self):
        """Run one monitor lifecycle."""
        basic_info_url = f"{self.config['http_server']}/api/clients/uploadBasicInfo?token={self.config['token']}"
        ws_url = self.config["http_server"].replace("http", "ws") + f"/api/clients/report?token={self.config['token']}"

        await self._push_basic_info(basic_info_url)
        await self._start_websocket_monitoring(ws_url, basic_info_url)

    async def _push_basic_info(self, url: str) -> bool:
        """Upload the basic info payload."""
        basic_info = await self.system_info.get_basic_info()

        Logger.info("Basic info upload payload:")
        Logger.info(json.dumps(basic_info, indent=2))
        print(json.dumps(basic_info, indent=1))
        Logger.debug("Uploading basic info to uploadBasicInfo endpoint", 1)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=basic_info) as response:
                    if response.status in (200, 201):
                        Logger.info("Basic info upload succeeded")
                        self.last_basic_info_report = time.time()
                        return True
                    else:
                        Logger.error(f"Basic info upload failed - HTTP: {response.status}")
                        return False
        except Exception as e:
            Logger.error(f"Basic info upload exception: {e}")
            return False

    async def _start_websocket_monitoring(self, ws_url: str, basic_info_url: str):
        """Start the websocket monitoring loop."""
        Logger.debug(f"Starting WebSocket monitor: {ws_url}", 2)

        try:
            async with websockets.connect(ws_url) as websocket:
                Logger.info("WebSocket connected, monitoring started")

                message_task = asyncio.create_task(self._handle_websocket_messages(websocket))
                monitoring_task = asyncio.create_task(self._monitoring_loop(websocket, basic_info_url))

                done, pending = await asyncio.wait(
                    [message_task, monitoring_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

        except Exception as e:
            Logger.error(f"WebSocket monitor exception: {e}")
        finally:
            Logger.info("WebSocket connection closed")

    async def _handle_websocket_messages(self, websocket):
        """Receive and process websocket messages."""
        try:
            async for message in websocket:
                try:
                    if isinstance(message, str):
                        event = json.loads(message)
                        Logger.debug(f"Received server message: {json.dumps(event, indent=2)}", 2)
                        await self.event_handler.handle_event(event)
                    else:
                        Logger.debug(f"Received binary message, length: {len(message)}", 2)
                except Exception as e:
                    Logger.error(f"Failed to handle WebSocket message: {e}")
        except Exception as e:
            Logger.error(f"WebSocket receive loop exception: {e}")

    async def _monitoring_loop(self, websocket, basic_info_url: str):
        """Send realtime metrics in a loop."""
        sequence = 0
        interval = max(0.1, self.config.get("interval", 1.0))

        while True:
            start_time = time.time()

            current_time = time.time()
            if current_time - self.last_basic_info_report >= self.BASIC_INFO_INTERVAL:
                success = await self._push_basic_info(basic_info_url)
                if success:
                    self.last_basic_info_report = current_time
                else:
                    self.last_basic_info_report = current_time - self.BASIC_INFO_INTERVAL + 30

            realtime_info = await self.system_info.get_realtime_info()

            Logger.debug(f"Sending realtime payload: {json.dumps(realtime_info, indent=2)}", 2)

            try:
                await websocket.send(json.dumps(realtime_info))
                sequence += 1
                Logger.debug(f"Sent realtime payload #{sequence}", 2)
            except Exception as e:
                Logger.error(f"Failed to send monitoring payload: {e}")
                break

            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)


def parse_args() -> Dict[str, Any]:
    """Parse CLI arguments."""
    args = {
        "http_server": None,
        "token": None,
        "interval": None,
        "reconnect_interval": None,
        "ignore_unsafe_cert": None,
        "log_level": None,
        "disable_remote_control": None,
        "include_nics": None,
    }

    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--http-server", "--endpoint", "-e") and i + 1 < len(argv):
            args["http_server"] = argv[i + 1]
            i += 1
        elif arg in ("--token", "-t") and i + 1 < len(argv):
            args["token"] = argv[i + 1]
            i += 1
        elif arg == "--interval" and i + 1 < len(argv):
            args["interval"] = float(argv[i + 1])
            i += 1
        elif arg == "--reconnect-interval" and i + 1 < len(argv):
            args["reconnect_interval"] = int(argv[i + 1])
            i += 1
        elif arg == "--log-level" and i + 1 < len(argv):
            args["log_level"] = int(argv[i + 1])
            i += 1
        elif arg == "--include-nics" and i + 1 < len(argv):
            args["include_nics"] = [nic.strip() for nic in argv[i + 1].split(",") if nic.strip()]
            i += 1
        elif arg == "--disable-web-ssh":
            args["disable_remote_control"] = True
        elif arg == "--enable-web-ssh":
            args["disable_remote_control"] = False
        elif arg == "--install-ghproxy" and i + 1 < len(argv):
            i += 1
        elif arg in ("--help", "-h"):
            _show_help()
            sys.exit(0)
        i += 1

    return args


def parse_env_args() -> Dict[str, Any]:
    """Parse environment-based configuration."""
    return {
        "http_server": os.getenv("KOMARI_HTTP_SERVER", ""),
        "token": os.getenv("KOMARI_TOKEN", ""),
        "interval": float(os.getenv("KOMARI_INTERVAL", "5.0")),
        "reconnect_interval": int(os.getenv("KOMARI_RECONNECT_INTERVAL", "10")),
        "ignore_unsafe_cert": os.getenv("KOMARI_IGNORE_UNSAFE_CERT", "true").lower() != "false",
        "log_level": int(os.getenv("KOMARI_LOG_LEVEL", "0")),
        "disable_remote_control": os.getenv("KOMARI_DISABLE_REMOTE_CONTROL", "false").lower() == "true",
        "include_nics": [nic.strip() for nic in os.getenv("KOMARI_INCLUDE_NICS", "").split(",") if nic.strip()],
    }


def merge_config(cli_config: dict, env_config: dict) -> dict:
    merged = env_config.copy()
    for key, value in cli_config.items():
        if value is not None:
            merged[key] = value
    return merged


def get_final_config() -> Dict[str, Any]:
    """Build the final runtime configuration."""
    cli_config = parse_args()
    env_config = parse_env_args()
    config = merge_config(cli_config, env_config)
    if not config["http_server"]:
        print("Error: --http-server is required, or set KOMARI_HTTP_SERVER.")
        _show_help()
        sys.exit(1)

    http_server = config.get("http_server", "")
    if isinstance(http_server, str):
        config["http_server"] = http_server.rstrip("/")

    if not config["token"]:
        print("Error: --token is required, or set KOMARI_TOKEN.")
        _show_help()
        sys.exit(1)

    return config


def _show_help():
    """Print help text."""
    print("komari-agent-python 1.0.0")
    print()
    print("Usage: python komari_agent.py --token <token> [options]")
    print()
    print("Options:")
    print("  --http-server <url>        Server URL (or KOMARI_HTTP_SERVER) [required]")
    print("  --token <token>            Auth token (or KOMARI_TOKEN) [required]")
    print("  --interval <sec>           Realtime report interval in seconds (default: 1.0)")
    print("  --reconnect-interval <sec> Reconnect interval in seconds")
    print("  --log-level <level>        0=off, 1=basic, 2=websocket, 3=terminal, 4=network, 5=disk")
    print("  --include-nics <list>      Comma-separated NIC allowlist")
    print("  --disable-web-ssh          Keep remote control disabled")
    print("  --enable-web-ssh           Compatibility flag only; remote control is still unavailable")
    print("  --help                     Show this help")
    print()
    print("Environment:")
    print("  CLI arguments override environment variables when both are present.")


async def check_environment() -> bool:
    """Check runtime prerequisites."""
    print("Checking runtime environment...")

    errors = []
    warnings = []

    python_version = sys.version_info
    if python_version < (3, 7):
        errors.append("Python 3.7 or newer is required.")
    else:
        print(f"[OK] Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")

    required_modules = [
        ("aiohttp", "aiohttp"),
        ("websockets", "websockets"),
        ("psutil", "psutil"),
    ]

    for module_name, package_name in required_modules:
        try:
            __import__(package_name)
            print(f"[OK] Python module available: {module_name}")
        except ImportError:
            errors.append(f"Missing required module: {module_name}. Install with: pip install {package_name}")

    if platform.system() != "Windows":
        required_commands = ["ping"]
        for cmd in required_commands:
            try:
                subprocess.run(["which", cmd], capture_output=True, check=True)
                print(f"[OK] System command available: {cmd}")
            except subprocess.CalledProcessError:
                warnings.append(f"Missing system command: {cmd}. Some features may be limited.")

    if platform.system() != "Windows":
        try:
            import pty

            print("[OK] PTY support available")
        except ImportError:
            warnings.append("PTY support is unavailable. Terminal features may be limited.")

    if warnings:
        print("\n[WARN] Warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print("\n[ERROR] Environment check failed:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("[OK] Environment check passed")
    return True


async def main():
    """Program entrypoint."""
    try:
        config = get_final_config()

        if await check_environment():
            Logger.set_log_level(config["log_level"])
            client = KomariMonitorClient(config)
            await client.run()
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        Logger.info("Program interrupted by user")
    except Exception as e:
        Logger.error(f"Program exception: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
