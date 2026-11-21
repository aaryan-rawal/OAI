from __future__ import annotations
import re, shutil, subprocess, tempfile
from pathlib import Path
from typing import Any

class OCRUnavailable(RuntimeError): pass

def _paddle(image_path: Path) -> tuple[str, float]:
    from paddleocr import PaddleOCR  # type: ignore
    engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    result = engine.ocr(str(image_path), cls=True) or []
    lines=[]; scores=[]
    for page in result:
        for item in page or []:
            if len(item) > 1 and item[1]:
                lines.append(str(item[1][0])); scores.append(float(item[1][1]))
    return "\n".join(lines), (sum(scores)/len(scores) if scores else 0.0)

def _tesseract(image_path: Path) -> tuple[str, float]:
    binary=shutil.which("tesseract")
    if not binary: raise OCRUnavailable("Neither PaddleOCR nor the Tesseract executable is available.")
    proc=subprocess.run([binary,str(image_path),"stdout","--psm","6","tsv"],capture_output=True,text=True,timeout=90,check=True)
    rows=proc.stdout.splitlines(); words=[]; confidences=[]
    for row in rows[1:]:
        cols=row.split("\t")
        if len(cols)>=12 and cols[11].strip():
            words.append(cols[11].strip())
            try:
                c=float(cols[10]);
                if c>=0: confidences.append(c/100)
            except ValueError: pass
    return " ".join(words), (sum(confidences)/len(confidences) if confidences else 0.0)

def _to_image(source: Path, suffix: str, work: Path) -> Path:
    if suffix in {".png",".jpg",".jpeg",".tif",".tiff",".bmp"}: return source
    if suffix == ".pdf":
        try:
            import pypdfium2 as pdfium  # type: ignore
            pdf=pdfium.PdfDocument(str(source));
            if len(pdf)<1: raise ValueError("PDF contains no pages")
            bitmap=pdf[0].render(scale=2); image=bitmap.to_pil(); target=work/"page1.png"; image.save(target); return target
        except ImportError:
            binary=shutil.which("pdftoppm")
            if not binary: raise OCRUnavailable("PDF OCR requires pypdfium2 or pdftoppm.")
            prefix=work/"page"; subprocess.run([binary,"-f","1","-l","1","-png","-r","200",str(source),str(prefix)],capture_output=True,timeout=90,check=True)
            target=work/"page-1.png"
            if not target.exists(): raise OCRUnavailable("Unable to render first PDF page.")
            return target
    raise ValueError("Unsupported OCR file type")

def extract_document(content: bytes, filename: str) -> dict[str, Any]:
    suffix=Path(filename).suffix.lower()
    if suffix not in {".pdf",".png",".jpg",".jpeg",".tif",".tiff",".bmp"}: raise ValueError("Supported formats: PDF, PNG, JPG, TIFF, BMP")
    with tempfile.TemporaryDirectory(prefix="of_ocr_") as tmp:
        work=Path(tmp); source=work/ f"source{suffix}"; source.write_bytes(content); image=_to_image(source,suffix,work)
        try:
            text,confidence=_paddle(image); engine="paddleocr"
            if not text.strip(): raise OCRUnavailable("PaddleOCR returned no text")
        except Exception as paddle_error:
            try: text,confidence=_tesseract(image); engine="tesseract"
            except Exception as tess_error: raise OCRUnavailable(f"OCR engines unavailable or failed. PaddleOCR: {paddle_error}; Tesseract: {tess_error}") from tess_error
    compact=re.sub(r"\s+"," ",text).strip()
    dob=re.search(r"\b(?:0?[1-9]|[12]\d|3[01])[/-](?:0?[1-9]|1[0-2])[/-](?:19|20)\d{2}\b",compact)
    licence=re.search(r"\b(?:DL\s*(?:NO|NUMBER)?\s*[:#-]?\s*)?([A-Z]{2}[- ]?\d{2}[- ]?\d{4}[- ]?\d{7})\b",compact,re.I)
    return {"engine":engine,"text":text,"average_confidence":round(confidence,4),"page_count_processed":1,
            "extracted_fields":{"date_of_birth_candidate":dob.group(0) if dob else None,"driving_licence_number_candidate":licence.group(1) if licence else None},
            "verification_status":"human_review_required","warning":"OCR output is unverified. It does not establish document authenticity, validity, identity, or licence class."}
