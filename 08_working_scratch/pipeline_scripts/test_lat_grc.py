"""Quick test: compare Tesseract lat vs lat+grc on pages 33-35."""
import json
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
import shutil

# Setup
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
tessdata = Path(r"C:\Users\User\Documents\UssherIn\06_tools_config\tessdata").resolve()
pdf = Path(r"C:\Users\User\Documents\UssherIn\00_source_pdf\JamesUssher_Britannicarum ecclesiarum antiquitates_Part1.pdf")
config_base = f"--oem 1 --tessdata-dir {tessdata} --psm 3"

images = convert_from_path(str(pdf), first_page=33, last_page=35, dpi=400)

results = []
for i, img in enumerate(images, start=33):
    for lang in ["lat", "lat+grc"]:
        data = pytesseract.image_to_data(img, lang=lang, config=config_base, output_type=pytesseract.Output.DICT)
        confs = [int(c) for c in data["conf"] if int(c) >= 0]
        avg_conf = sum(confs) / len(confs) if confs else 0
        text = pytesseract.image_to_string(img, lang=lang, config=config_base)
        results.append({
            "page": i,
            "lang": lang,
            "chars": len(text),
            "avg_conf": round(avg_conf, 2),
            "lines": text.count("\n") + 1,
        })
        # Save text for comparison
        out = Path(f"08_working_scratch/test_lat_grc_p{i:04d}_{lang.replace('+','_')}.txt")
        out.write_text(text, encoding="utf-8")
        print(f"  Page {i} [{lang}]: {len(text)} chars, conf={avg_conf:.1f}%")

print("\n=== Summary ===")
print(f"{'Page':<6} {'Lang':<10} {'Chars':<8} {'Conf':<8} {'Lines':<6}")
for r in results:
    print(f"{r['page']:<6} {r['lang']:<10} {r['chars']:<8} {r['avg_conf']:<8} {r['lines']:<6}")
