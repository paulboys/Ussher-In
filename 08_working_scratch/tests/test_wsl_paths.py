"""Tests for WSL path conversion helpers."""

from wsl_paths import windows_to_wsl, wsl_to_windows


def test_windows_to_wsl_c_drive() -> None:
    result = windows_to_wsl("C:\\Users\\User\\file.pdf")
    assert result == "/mnt/c/Users/User/file.pdf"


def test_windows_to_wsl_d_drive() -> None:
    result = windows_to_wsl("D:\\Data\\image.tif")
    assert result == "/mnt/d/Data/image.tif"


def test_windows_to_wsl_forward_slashes() -> None:
    result = windows_to_wsl("C:/Users/User/file.pdf")
    assert result == "/mnt/c/Users/User/file.pdf"


def test_wsl_to_windows_roundtrip() -> None:
    original = "C:\\Users\\User\\Documents\\file.txt"
    wsl = windows_to_wsl(original)
    back = wsl_to_windows(wsl)
    assert str(back) == "C:\\Users\\User\\Documents\\file.txt"
