# Tool Installation Guide (Windows)

## 1. OCR Engine Setup

### Option A: Kraken via WSL (Recommended)

Kraken is the primary OCR engine. It runs inside WSL (Windows Subsystem for Linux).

See `06_tools_config/wsl_kraken_setup.md` for full setup instructions.

Quick summary:

```powershell
# Install WSL (requires restart)
wsl --install --no-launch

# After restart, install Ubuntu
wsl --install -d Ubuntu

# Inside Ubuntu, install Kraken
sudo apt update && sudo apt install -y python3 python3-pip python3-venv
python3 -m venv ~/kraken-env
source ~/kraken-env/bin/activate
pip install kraken
kraken get default
```

### Option B: Tesseract (Fallback)

Tesseract 5.x with Latin data is retained as a fallback engine.

Verification commands:

```powershell
tesseract --version
tesseract --list-langs
```

Ensure `lat` appears in available languages.

## 2. Optional PDF/Image utilities

Use one of the following for preprocessing and page extraction:
- Ghostscript
- ImageMagick

## 3. Python environment

Use a dedicated environment for scripts in `08_working_scratch/pipeline_scripts/`.

Recommended packages are listed in `06_tools_config/python_env_requirements.txt`.

For WSL/Kraken dependencies, see `06_tools_config/python_wsl_requirements.txt`.

## 4. Pilot readiness check

Before pilot OCR:
- Source PDFs present in `00_source_pdf/`
- OCR engine reachable:
  - Kraken: `wsl -- bash -c "source ~/kraken-env/bin/activate && kraken --version"`
  - Tesseract: `tesseract --version`
- Output directories exist under `01_raw_ocr_output/`

## 5. Running OCR

Default (Kraken via WSL):

```powershell
.\scripts\Invoke-KrakenOcr.ps1 -PdfPath "00_source_pdf\JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf" -Part part1 -StartPage 30 -EndPage 35
```

Fallback (Tesseract):

```powershell
.\scripts\Invoke-KrakenOcr.ps1 -PdfPath "00_source_pdf\JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf" -Part part1 -StartPage 30 -EndPage 35 -OcrEngine tesseract
```
