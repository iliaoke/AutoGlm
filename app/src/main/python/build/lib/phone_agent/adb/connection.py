"""ADB connection management for local and remote devices."""

import os
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from phone_agent.config.timing import TIMING_CONFIG


class ConnectionType(Enum):
    """Type of ADB connection."""

    USB = "usb"
    WIFI = "wifi"
    REMOTE = "remote"


@dataclass
class DeviceInfo:
    """Information about a connected device."""

    device_id: str
    status: str
    connection_type: ConnectionType
    model: str | None = None
    android_version: str | None = None


class ADBConnection:
    """
    Manages ADB connections to Android devices.
    """

    def __init__(self, adb_path: str | None = None):
        """
        Initialize ADB connection manager.
        """
        self.adb_path = adb_path or os.getenv("PHONE_AGENT_ADB_PATH", "adb")

    def connect(self, address: str, timeout: int = 10) -> tuple[bool, str]:
        if ":" not in address:
            address = f"{address}:5555"

        try:
            result = subprocess.run(
                [self.adb_path, "connect", address],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            output = result.stdout + result.stderr

            if "connected" in output.lower():
                return True, f"Connected to {address}"
            elif "already connected" in output.lower():
                return True, f"Already connected to {address}"
            else:
                return False, output.strip()

        except Exception as e:
            return False, f"Connection error: {e}"

    def disconnect(self, address: str | None = None) -> tuple[bool, str]:
        try:
            cmd = [self.adb_path, "disconnect"]
            if address:
                cmd.append(address)

            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=5)

            output = result.stdout + result.stderr
            return True, output.strip() or "Disconnected"

        except Exception as e:
            return False, f"Disconnect error: {e}"

    def list_devices(self) -> list[DeviceInfo]:
        try:
            result = subprocess.run(
                [self.adb_path, "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            devices = []
            for line in result.stdout.strip().split("\n")[1:]:
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    status = parts[1]

                    if ":" in device_id:
                        conn_type = ConnectionType.REMOTE
                    else:
                        conn_type = ConnectionType.USB

                    model = None
                    for part in parts[2:]:
                        if part.startswith("model:"):
                            model = part.split(":", 1)[1]
                            break

                    devices.append(
                        DeviceInfo(
                            device_id=device_id,
                            status=status,
                            connection_type=conn_type,
                            model=model,
                        )
                    )

            return devices

        except Exception as e:
            print(f"Error listing devices: {e}")
            return []

    def enable_tcpip(
        self, port: int = 5555, device_id: str | None = None
    ) -> tuple[bool, str]:
        try:
            cmd = [self.adb_path]
            if device_id:
                cmd.extend(["-s", device_id])
            cmd.extend(["tcpip", str(port)])

            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=10)
            output = result.stdout + result.stderr

            if "restarting" in output.lower() or result.returncode == 0:
                time.sleep(TIMING_CONFIG.connection.adb_restart_delay)
                return True, f"TCP/IP mode enabled on port {port}"
            else:
                return False, output.strip()
        except Exception as e:
            return False, f"Error enabling TCP/IP: {e}"

    def get_device_ip(self, device_id: str | None = None) -> str | None:
        try:
            cmd = [self.adb_path]
            if device_id:
                cmd.extend(["-s", device_id])

            # Try wlan0 interface
            result = subprocess.run(
                cmd + ["shell", "ip", "addr", "show", "wlan0"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=5,
            )

            for line in result.stdout.split("\n"):
                if "inet " in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        return parts[1].split("/")[0]
            return None
        except Exception as e:
            print(f"Error getting device IP: {e}")
            return None


def quick_connect(address: str) -> tuple[bool, str]:
    conn = ADBConnection()
    return conn.connect(address)


def list_devices() -> list[DeviceInfo]:
    conn = ADBConnection()
    return conn.list_devices()
