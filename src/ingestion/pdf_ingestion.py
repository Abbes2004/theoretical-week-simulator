"""Read-only text extraction from the purchase-order PDFs under
data/raw/pdf/.

Evidence (docs/analysis/TASK2_Supporting_Sources_Business_Mapping.md): the
two PDFs are finished-goods sales orders and contain no identifier that
overlaps with POI_Sim, Id_Sim, or Code_Sim. They are therefore NOT used by
the canonical dataset or the business-rule engine. This module exists only
to make their content searchable/citable as documentation lineage
(MASTER_PROMPT.md section 5, "Additional files ... must be analyzed before
assuming ... a business rule").
"""

from __future__ import annotations

import sys
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from configs import settings  # noqa: E402


def extract_text(pdf_path: str | Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def ingest_all_pdfs(write_interim: bool = True) -> dict[str, str]:
    """Returns {filename: extracted_text}. Writes a .txt sidecar per PDF
    under data/interim/pdf_text/ when write_interim is True.
    """
    out_dir = settings.DATA_INTERIM / "pdf_text"
    if write_interim:
        out_dir.mkdir(parents=True, exist_ok=True)

    texts: dict[str, str] = {}
    for pdf_path in settings.RAW_PDF_FILES:
        text = extract_text(pdf_path)
        texts[pdf_path.name] = text
        if write_interim:
            (out_dir / f"{pdf_path.stem}.txt").write_text(text, encoding="utf-8")
    return texts


if __name__ == "__main__":
    texts = ingest_all_pdfs()
    for name, text in texts.items():
        print(f"{name}: {len(text):,} characters extracted")
