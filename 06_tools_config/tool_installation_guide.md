# Tool Installation Guide (Windows)

## 1. Install Tesseract

Recommended: Tesseract 5.x with Latin data.

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

## 4. Pilot readiness check

Before pilot OCR:
- Source PDFs present in `00_source_pdf/`
- Tesseract reachable in terminal
- Output directories exist under `01_raw_ocr_output/`
