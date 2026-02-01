"""Screenshot utilities for capturing Android device screen."""

import base64
import os
import subprocess
from dataclasses import dataclass
from io import BytesIO
from PIL import Image

@dataclass
class Screenshot:
    """Represents a captured screenshot."""
    base64_data: str
    width: int
    height: int
    is_sensitive: bool = False

def get_screenshot(device_id: str | None = None, timeout: int = 20) -> Screenshot:
    """
    Capture a screenshot from the connected Android device using stdout pipe.
    """
    adb_path = os.getenv("PHONE_AGENT_ADB_PATH", "adb")

    # Use -s if device_id is provided, otherwise let adb decide
    cmd = [adb_path]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "screencap", "-p"])

    try:
        print(f"📸 Executing: {' '.join(cmd)}")
        # Run process and capture raw bytes
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout
        )

        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='ignore').strip()
            print(f"❌ screencap command failed (code {result.returncode}): {stderr}")
            return _create_fallback_screenshot(is_sensitive=False)

        raw_data = result.stdout
        if not raw_data:
            print("❌ screencap returned empty output")
            return _create_fallback_screenshot(is_sensitive=False)

        # Detect PNG header (89 50 4E 47 0D 0A 1A 0A)
        # Sometimes ADB or transport layer might prepend text or corrupt line endings
        png_header = b'\x89PNG'
        idx = raw_data.find(png_header)

        data = None
        if idx != -1:
            data = raw_data[idx:]
        else:
            # Check if it's corrupted by CRLF translation (common on some ADB/shell setups)
            fixed_data = raw_data.replace(b'\r\n', b'\n')
            idx = fixed_data.find(png_header)
            if idx != -1:
                print("⚠️ Detected and fixed CRLF corruption in screenshot data")
                data = fixed_data[idx:]
            else:
                print(f"❌ No PNG header found in output (size: {len(raw_data)})")
                if len(raw_data) > 0:
                    print(f"   Output preview: {raw_data[:100]!r}")
                return _create_fallback_screenshot(is_sensitive=True)

        # Attempt to open the image
        try:
            img = Image.open(BytesIO(data))
            # Force loading the image to catch any decode errors early
            img.verify()
            # Re-open because verify() closes it or moves the pointer
            img = Image.open(BytesIO(data))

            width, height = img.size

            # Re-save to normalize and get base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

            return Screenshot(
                base64_data=base64_data,
                width=width,
                height=height,
                is_sensitive=False
            )
        except Exception as img_e:
            print(f"❌ Failed to decode screenshot image: {img_e}")
            return _create_fallback_screenshot(is_sensitive=True)

    except subprocess.TimeoutExpired:
        print(f"❌ Screenshot command timed out after {timeout}s")
        return _create_fallback_screenshot(is_sensitive=False)
    except Exception as e:
        print(f"❌ Screenshot exception: {e}")
        return _create_fallback_screenshot(is_sensitive=False)

def _create_fallback_screenshot(is_sensitive: bool) -> Screenshot:
    """Create a black fallback image when screenshot fails."""
    # Standard phone resolution as fallback
    default_width, default_height = 1080, 2400

    black_img = Image.new("RGB", (default_width, default_height), color="black")
    buffered = BytesIO()
    black_img.save(buffered, format="PNG")
    base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return Screenshot(
        base64_data=base64_data,
        width=default_width,
        height=default_height,
        is_sensitive=is_sensitive,
    )
