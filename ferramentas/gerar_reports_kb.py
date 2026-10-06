#!/usr/bin/env python3
"""Extrai texto dos PDFs de reports/ para data/kb/ (Ask Sergio AI)."""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
REPORTS_JSON = ROOT / "data" / "reports.json"
KB_DIR = ROOT / "data" / "kb"
INDEX = KB_DIR / "index.json"


def clean(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return clean("\n".join(parts))


def paragraphs(text: str) -> list[str]:
    # Keep reasonably sized blocks for later client scoring.
    raw = re.split(r"\n\s*\n|(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÀÃÕÂÊÔÜ])", text)
    out: list[str] = []
    buf = ""
    for p in raw:
        p = clean(p)
        if len(p) < 40:
            buf = (buf + " " + p).strip()
            continue
        chunk = (buf + " " + p).strip() if buf else p
        buf = ""
        if len(chunk) > 1200:
            for i in range(0, len(chunk), 900):
                out.append(chunk[i : i + 1000].strip())
        else:
            out.append(chunk)
    if buf and len(buf) >= 40:
        out.append(buf)
    return out


def main() -> int:
    meta = json.loads(REPORTS_JSON.read_text(encoding="utf-8"))
    KB_DIR.mkdir(parents=True, exist_ok=True)
    # Remove old txts so deleted reports disappear
    for old in KB_DIR.glob("*.txt"):
        old.unlink()

    index: list[dict] = []
    errors: list[str] = []

    for r in meta.get("relatorios") or []:
        rid = r.get("id")
        ficheiro = r.get("ficheiro")
        if not isinstance(rid, str) or not isinstance(ficheiro, str):
            continue
        pdf = ROOT / ficheiro
        if not pdf.is_file():
            errors.append(f"missing {ficheiro}")
            continue
        try:
            text = extract_pdf(pdf)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{rid}: {exc}")
            continue
        if len(text) < 40:
            errors.append(f"{rid}: empty text")
            continue

        paras = paragraphs(text)
        # Paragraph file fetched on demand by Ask Sergio AI for matched reports.
        (KB_DIR / f"{rid}.paras.json").write_text(
            json.dumps(paras, ensure_ascii=False),
            encoding="utf-8",
        )

        index.append(
            {
                "id": rid,
                "titulo": r.get("titulo") or {},
                "resumo": r.get("resumo") or {},
                "descricao": r.get("descricao") or {},
                "areas": r.get("areas") or [],
                "genes": (r.get("genes") or [])[:80],
                "palavras": r.get("palavras") or [],
                "destaque": bool(r.get("destaque")),
                "chars": len(text),
                "paras": len(paras),
                "preview": text[:2200],
                "paras_file": f"data/kb/{rid}.paras.json",
            }
        )
        print(f"ok {rid} chars={len(text)} paras={len(paras)}", flush=True)

    INDEX.write_text(
        json.dumps(
            {
                "gerado_em": date.today().isoformat(),
                "fonte": "reports/*.pdf + data/reports.json",
                "n": len(index),
                "reports": index,
            },
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {INDEX} n={len(index)}", flush=True)
    if errors:
        print("errors:", *errors, sep="\n- ", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
