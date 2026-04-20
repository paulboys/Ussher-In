# Kraken OCR Setup via WSL (Windows)

## Prerequisites

- Windows 10 (build 19041+) or Windows 11
- WSL2 enabled (see step 1 below)
- At least 4 GB free disk space for Ubuntu + Kraken + models

## 1. Install WSL2 and Ubuntu

From an **elevated** PowerShell prompt:

```powershell
wsl --install --no-launch
```

**Restart your computer**, then open PowerShell and run:

```powershell
wsl --install -d Ubuntu
```

Follow the prompts to create a username and password for the Ubuntu instance.

Verify:

```powershell
wsl --list --verbose
```

You should see `Ubuntu` with `VERSION 2`.

## 2. Install Kraken inside WSL

Open the Ubuntu terminal (or run `wsl` from PowerShell):

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git
```

Create a dedicated virtual environment:

```bash
python3 -m venv ~/kraken-env
source ~/kraken-env/bin/activate
pip install --upgrade pip
pip install kraken
```

Verify:

```bash
kraken --version
```

## 3. Download a baseline Latin model

Kraken ships community models. To list available models:

```bash
kraken list
```

Download the default model (or a specific Latin model if available):

```bash
kraken get default
```

For Latin early-modern print, search for a suitable model:

```bash
kraken list | grep -i latin
```

If no specialized Latin model is available, the default model will serve as a starting point for fine-tuning.

## 4. Path mapping (Windows to WSL)

Windows paths are accessible inside WSL under `/mnt/`:

| Windows path | WSL path |
|---|---|
| `C:\Users\User\Documents\UssherIn` | `/mnt/c/Users/User/Documents/UssherIn` |
| `C:\Users\User\Documents\UssherIn\00_source_pdf\file.pdf` | `/mnt/c/Users/User/Documents/UssherIn/00_source_pdf/file.pdf` |

The project provides automatic path conversion in the wrapper scripts.

## 5. Run OCR from Windows (PowerShell wrapper)

Use the provided wrapper script:

```powershell
.\scripts\Invoke-KrakenOcr.ps1 -PdfPath "00_source_pdf\JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf" -Part part1 -StartPage 30 -EndPage 35
```

This invokes Kraken inside WSL, converts paths automatically, and writes output to `01_raw_ocr_output/`.

## 6. Verify end-to-end

```powershell
# Quick smoke test: OCR a single page
.\scripts\Invoke-KrakenOcr.ps1 -PdfPath "00_source_pdf\JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf" -Part part1 -StartPage 30 -EndPage 30
```

Check that `01_raw_ocr_output/part1/page_0030_raw.txt` contains extracted text.

## Troubleshooting

- **WSL_E_WSL_OPTIONAL_COMPONENT_REQUIRED**: Restart your computer after `wsl --install`.
- **Permission denied on /mnt/c/...**: Run `sudo chmod` or check Windows file permissions.
- **kraken: command not found**: Activate the virtual environment first: `source ~/kraken-env/bin/activate`.
- **Model not found**: Run `kraken get default` to download a baseline model.
