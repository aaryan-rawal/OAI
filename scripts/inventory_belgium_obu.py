#!/usr/bin/env python3
"""Create a privacy-conscious inventory of a locally extracted Belgium OBU dataset.

Streams large CSV/TSV files; does not copy dataset contents. Cell values are never
written to the report. Only filenames, sizes, positional column metadata, sampled type hints and
sample counts are recorded. No header is assumed by default.
"""
from __future__ import annotations
import argparse, csv, json, math, mimetypes, os, struct
from collections import Counter
from pathlib import Path
from typing import Iterable

SAMPLE_ROWS = 50


def guess_type(values: list[str]) -> str:
    vals = [v.strip() for v in values if v and v.strip()]
    if not vals:
        return "empty_or_unknown"
    def is_int(s: str) -> bool:
        try: int(s); return True
        except ValueError: return False
    def is_float(s: str) -> bool:
        try: return math.isfinite(float(s))
        except ValueError: return False
    if all(is_int(v) for v in vals): return "integer_like"
    if all(is_float(v) for v in vals): return "numeric_like"
    low = [v.lower() for v in vals]
    if all(v in {"true", "false", "yes", "no", "0", "1"} for v in low): return "boolean_like"
    return "text_or_identifier"


def sniff_delimiter(path: Path) -> str:
    if path.suffix.lower() == ".tsv": return "\t"
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(65536)
    try: return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error: return ","


def csv_info(path: Path) -> dict:
    """Inspect headerless time-series CSVs without assuming row 1 is a header.

    The Belgium OBU inventory's first pass showed timestamp/numeric values being
    mistaken for column names. This version treats every row as data and reports
    positional fields only; it never writes sampled cell values.
    """
    delimiter = sniff_delimiter(path)
    values: list[list[str]] = []
    sampled_rows = 0
    malformed_rows = 0
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            if not row:
                continue
            if not values:
                values = [[] for _ in row]
            if len(row) != len(values):
                malformed_rows += 1
                if len(row) > len(values):
                    values.extend([[] for _ in range(len(row) - len(values))])
            for i in range(len(values)):
                values[i].append(row[i] if i < len(row) else "")
            sampled_rows += 1
            if sampled_rows >= SAMPLE_ROWS:
                break
    return {
        "format": "csv/tsv",
        "header_assumption": "headerless; first row treated as data pending dataset documentation",
        "delimiter": "TAB" if delimiter == "\t" else delimiter,
        "column_count": len(values),
        "columns": [
            {"index": i, "sampled_type": guess_type(col),
             "sampled_nonempty": sum(bool(v.strip()) for v in col)}
            for i, col in enumerate(values)
        ],
        "sampled_rows": sampled_rows,
        "rows_with_unexpected_column_count": malformed_rows,
        "note": "Only up to 50 data rows were sampled. Cell values are intentionally excluded; field meanings require dataset documentation.",
    }


def file_signature(path: Path) -> str:
    try:
        with path.open("rb") as f: head = f.read(16)
    except OSError: return "unreadable"
    if head.startswith(b"PAR1"): return "parquet"
    if head.startswith(b"PK\x03\x04"): return "zip_container_or_office_file"
    if head.startswith(b"%PDF"): return "pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"): return "png"
    if head.startswith(b"\xff\xd8\xff"): return "jpeg"
    if head.startswith((b"II*\x00", b"MM\x00*")): return "tiff"
    if head.startswith(b"SQLite format 3\x00"): return "sqlite"
    return "unknown_or_text"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dataset_folder", help="Root folder containing the extracted dataset")
    p.add_argument("--output", default="belgium_obu_inventory", help="Output filename prefix")
    args = p.parse_args()
    root = Path(args.dataset_folder).expanduser().resolve()
    if not root.is_dir():
        p.error(f"Dataset folder does not exist: {root}")
    entries = []
    totals = Counter()
    for path in sorted(x for x in root.rglob("*") if x.is_file()):
        rel = str(path.relative_to(root))
        size = path.stat().st_size
        ext = path.suffix.lower() or "[no extension]"
        item = {"relative_path": rel, "extension": ext, "size_bytes": size,
                "size_mb": round(size / (1024 * 1024), 3), "signature": file_signature(path)}
        if ext in {".csv", ".tsv"}:
            try: item["details"] = csv_info(path)
            except Exception as exc: item["inspection_error"] = type(exc).__name__
        elif ext in {".jsonl", ".ndjson"}:
            item["details"] = {"format": "json-lines", "note": "Not parsed; content not copied."}
        elif ext == ".parquet":
            item["details"] = {"format": "parquet", "note": "Install pyarrow locally if schema inspection is needed."}
        entries.append(item)
        totals[ext] += 1
    report = {"dataset_root_name": root.name, "file_count": len(entries),
              "total_size_bytes": sum(x["size_bytes"] for x in entries),
              "counts_by_extension": dict(totals), "files": entries,
              "privacy": "No cell values, document contents, names, phone numbers or precise location records are exported."}
    out = Path(args.output).expanduser().resolve()
    if out.suffix.lower() == ".json": out = out.with_suffix("")
    json_path = out.with_suffix(".json")
    csv_path = out.with_name(out.name + "_files.csv")
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["relative_path", "extension", "size_bytes", "size_mb", "signature"])
        writer.writeheader()
        for item in entries: writer.writerow({k: item.get(k) for k in writer.fieldnames})
    print(f"Inventory complete: {len(entries)} files")
    print(f"JSON report: {json_path}")
    print(f"File list:   {csv_path}")
    print("No dataset cell values were included.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
