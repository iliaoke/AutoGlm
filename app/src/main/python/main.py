#!/usr/bin/env python3
"""
Phone Agent CLI - AI-powered phone automation.
"""

import argparse
import os
import shutil
import subprocess
import sys
from urllib.parse import urlparse

from openai import OpenAI

from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.agent_ios import IOSAgentConfig, IOSPhoneAgent
from phone_agent.config.apps import list_supported_apps
from phone_agent.config.apps_harmonyos import list_supported_apps as list_harmonyos_apps
from phone_agent.config.apps_ios import list_supported_apps as list_ios_apps
from phone_agent.device_factory import DeviceType, get_device_factory, set_device_type
from phone_agent.model import ModelConfig
from phone_agent.xctest import XCTestConnection
from phone_agent.xctest import list_devices as list_ios_devices


def check_system_requirements(
    device_type: DeviceType = DeviceType.ADB,
    wda_url: str = "http://localhost:8100",
    adb_path: str = "adb"
) -> bool:
    """
    Check system requirements before running the agent.
    """
    print("🔍 Checking system requirements...")
    print(f"ADB Path in use: {adb_path}")
    print("-" * 50)

    all_passed = True

    if device_type == DeviceType.IOS:
        tool_name = "libimobiledevice"
        tool_cmd = "idevice_id"
    else:
        tool_name = "ADB" if device_type == DeviceType.ADB else "HDC"
        tool_cmd = adb_path if device_type == DeviceType.ADB else "hdc"

    print(f"1. Checking {tool_name} availability...", end=" ")

    executable_exists = False
    if os.path.isabs(tool_cmd):
        executable_exists = os.path.exists(tool_cmd)
    else:
        executable_exists = shutil.which(tool_cmd) is not None

    if not executable_exists:
        print(f"❌ FAILED (Not found at {tool_cmd})")
        all_passed = False
    else:
        try:
            if device_type == DeviceType.ADB:
                version_cmd = [tool_cmd, "version"]
            elif device_type == DeviceType.HDC:
                version_cmd = [tool_cmd, "-v"]
            else:
                version_cmd = [tool_cmd, "-ln"]

            result = subprocess.run(version_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ OK")
            else:
                print(f"✅ OK (file exists)")
        except Exception as e:
            if os.path.exists(tool_cmd):
                print(f"✅ OK (exists)")
            else:
                print(f"❌ FAILED ({e})")
                all_passed = False

    if not all_passed: return False

    print("2. Checking connected devices...", end=" ")
    try:
        if device_type == DeviceType.ADB:
            result = subprocess.run([tool_cmd, "devices"], capture_output=True, text=True, timeout=10)
            lines = result.stdout.strip().split("\n")
            devices = [line for line in lines[1:] if line.strip() and "\tdevice" in line]
        elif device_type == DeviceType.HDC:
            result = subprocess.run(["hdc", "list", "targets"], capture_output=True, text=True, timeout=10)
            lines = result.stdout.strip().split("\n")
            devices = [line for line in lines if line.strip()]
        else:
            ios_devices = list_ios_devices()
            devices = [d.device_id for d in ios_devices]

        if not devices:
            print("❌ No devices")
            all_passed = False
        else:
            print(f"✅ OK ({len(devices)} device(s))")
    except Exception as e:
        print(f"❌ Error: {e}")
        all_passed = False

    print("-" * 50)
    return all_passed


def check_model_api(base_url: str, model_name: str, api_key: str = "EMPTY") -> bool:
    print(f"🔍 Checking model API: {model_name}...")
    try:
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=30.0)
        client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        print("✅ OK")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def main(*argv):
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Phone Agent", add_help=False)
    parser.add_argument("--base-url", type=str)
    parser.add_argument("--model", type=str)
    parser.add_argument("--apikey", type=str)
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--device-id", "-d", type=str)
    parser.add_argument("--adb-path", type=str, default="adb")
    parser.add_argument("--device-type", type=str, default="adb")
    parser.add_argument("--lang", type=str, default="cn")
    parser.add_argument("--quiet", "-q", action="store_true")
    parser.add_argument("task", nargs="?", type=str)

    try:
        # Convert argv to list if it's from callAttr
        args_list = []
        if argv:
            for a in argv:
                if isinstance(a, list):
                    args_list.extend([str(item) for item in a])
                else:
                    args_list.append(str(a))
        else:
            args_list = sys.argv[1:]

        print(f"Debug: Final args_list: {args_list}")

        # Use parse_known_args to be extra safe
        args, unknown = parser.parse_known_args(args_list)

        # Heuristic to find task if positional parsing failed
        if not args.task and unknown:
            for item in unknown:
                if not item.startswith("-"):
                    args.task = item
                    break

        if not args.task:
            return "Error: No task provided."

    except SystemExit as e:
        return f"Argument parsing failed with SystemExit (code {e.code}). Args: {args_list}"
    except Exception as e:
        return f"Error parsing arguments: {e}"

    # Set environment
    os.environ["PHONE_AGENT_ADB_PATH"] = args.adb_path or "adb"

    if args.device_type == "adb": device_type = DeviceType.ADB
    elif args.device_type == "hdc": device_type = DeviceType.HDC
    else: device_type = DeviceType.IOS

    if device_type != DeviceType.IOS: set_device_type(device_type)

    # 自动选择设备逻辑 (解决 "more than one device" 报错)
    if device_type == DeviceType.ADB and not args.device_id:
        try:
            from phone_agent.adb.connection import list_devices
            connected_devices = list_devices()
            if connected_devices:
                # 选取第一个状态为 "device" 的设备
                target_dev = None
                for dev in connected_devices:
                    if dev.status == "device":
                        target_dev = dev
                        break

                if target_dev:
                    args.device_id = target_dev.device_id
                    print(f"💡 Auto-selected device: {args.device_id}")
        except Exception as e:
            print(f"⚠️ Auto-selection failed: {e}")

    # Validate
    if not check_system_requirements(device_type, adb_path=os.environ["PHONE_AGENT_ADB_PATH"]):
        return "Error: System requirements not met."

    if not check_model_api(args.base_url, args.model, args.apikey):
        return "Error: Model API unreachable."

    # Run
    model_config = ModelConfig(base_url=args.base_url, model_name=args.model, api_key=args.apikey, lang=args.lang)
    agent_config = AgentConfig(max_steps=args.max_steps, device_id=args.device_id, verbose=not args.quiet, lang=args.lang)

    agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
    print(f"\n🚀 Phone Agent started (Device: {args.device_id or 'Auto'}). Task: {args.task}")

    try:
        return str(agent.run(args.task))
    except Exception as e:
        import traceback
        return f"Runtime error: {e}\n{traceback.format_exc()}"


if __name__ == "__main__":
    main()
