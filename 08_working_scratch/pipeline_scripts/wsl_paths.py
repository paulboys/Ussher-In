"""Cross-platform path helpers for Windows-to-WSL path conversion."""

from __future__ import annotations

import platform
import re
import subprocess
from pathlib import Path, PurePosixPath


def is_windows() -> bool:
    return platform.system() == "Windows"


def windows_to_wsl(path: str | Path) -> str:
    """Convert a Windows absolute path to the equivalent WSL /mnt/ path.

    Examples:
        C:\\Users\\User\\file.pdf -> /mnt/c/Users/User/file.pdf
        D:\\Data\\image.tif      -> /mnt/d/Data/image.tif
    """
    raw = str(path)
    match = re.match(r"^([A-Za-z]):[/\\](.*)$", raw)
    if not match:
        raise ValueError(f"Not a Windows absolute path: {raw}")

    drive_letter = match.group(1).lower()
    rest = match.group(2).replace("\\", "/")
    return f"/mnt/{drive_letter}/{rest}"


def wsl_to_windows(wsl_path: str) -> Path:
    """Convert a WSL /mnt/ path back to a Windows Path.

    Examples:
        /mnt/c/Users/User/file.pdf -> C:\\Users\\User\\file.pdf
    """
    match = re.match(r"^/mnt/([a-z])/(.*)$", wsl_path)
    if not match:
        raise ValueError(f"Not a WSL /mnt/ path: {wsl_path}")

    drive_letter = match.group(1).upper()
    rest = match.group(2)
    return Path(f"{drive_letter}:/{rest}")


def run_in_wsl(
    command: list[str],
    *,
    capture_output: bool = True,
    check: bool = True,
    timeout: int | None = 600,
) -> subprocess.CompletedProcess[str]:
    """Run a command inside WSL from Windows.

    Args:
        command: Command and arguments to execute inside WSL.
        capture_output: Whether to capture stdout/stderr.
        check: Whether to raise on non-zero exit code.
        timeout: Timeout in seconds (default 10 minutes).

    Returns:
        CompletedProcess with text-mode stdout/stderr.
    """
    wsl_cmd = ["wsl", "--"] + command
    return subprocess.run(
        wsl_cmd,
        capture_output=capture_output,
        text=True,
        check=check,
        timeout=timeout,
    )


def ensure_wsl_available() -> bool:
    """Check whether WSL is installed and a distribution is available."""
    if not is_windows():
        return False
    try:
        result = subprocess.run(
            ["wsl", "--list", "--quiet"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
