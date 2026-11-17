"""
FlyWise Phase 3: PDF -> cleaned, page-bounded, overlapping chunks.

Input:
  pdfs/*.pdf  (official Air India policy documents)

Output:
  data/flywise_air_india_chunks_v3.csv   (+ .jsonl)

Run:
  python prepare_chunks.py
  python prepare_chunks.py --target-words 110 --overlap-words 25

Chunking strategy (and why):
  * Page-bounded: a chunk never spans two PDF pages, so every answer can cite an
    exact page number.
  * Sentence-packed to ~110 words (hard max ~160): policy clauses are short, and
    small chunks keep one rule together without mixing in unrelated clauses.
  * Overlap: the last ~25 words of the previous chunk on the same page are
    prepended to the next chunk, so a clause split across a boundary is still
    retrievable. (In v2 the overlap was only stored as metadata and was never
    embedded; v3 embeds it.)
  * Metadata header: document, audience, effective date and page are written
    into the chunk text so both BM25 and embeddings can use them.
  * Cleaning: whitespace normalisation, removal of empty/very short pages,
    page-number-only lines and exact duplicate chunks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import pandas as pd

try:
    import pymupdf  # PyMuPDF >= 1.24
except ImportError:  # pragma: no cover
    import fitz as pymupdf

ROOT = Path(__file__).resolve().parent
PDF_DIR = ROOT / "pdfs"
OUT_CSV = ROOT / "data" / "flywise_air_india_chunks_v3.csv"

# Per-document metadata. Effective dates come from the documents themselves;
# "Not stated in supplied PDF" is used when the PDF gives none.
DOCUMENTS = {
    "air-india-coc.pdf": {
        "document_title": "Air India Conditions of Carriage",
        "audience": "Passenger-facing",
        "effective_date": "Not stated in supplied PDF",
        "topic": "Conditions of Carriage",
        "is_historical": False,
    },
    "ai-pets-in-cabin-guidelines.pdf": {
        "document_title": "Air India Pets in Cabin Guidelines",
        "audience": "Passenger-facing",
        "effective_date": "Not stated in supplied PDF",
        "topic": "Pets in cabin and pet documentation",
        "is_historical": False,
    },
    "air-india-hand-baggage-policy.pdf": {
        "document_title": "Air India Hand Baggage Policy",
        "audience": "Passenger-facing",
        "effective_date": "2015-07-01; historical",
        "topic": "Hand baggage allowance and permitted items (2015 document)",
        "is_historical": True,
    },
    "air-india-general-booking-policies-mar2026.pdf": {
        "document_title": "Air India General Booking Policies",
        "audience": "Primarily agent-facing",
        "effective_date": "2026-03",
        "topic": "Booking and ticketing",
        "is_historical": False,
    },
    "air-india-schedule-change-and-irrops-policy-may25.pdf": {
        "document_title": "Air India Schedule Change & IRROPS Policy",
        "audience": "Travel partner / operations-facing",
        "effective_date": "2025-05-21",
        "topic": "Schedule changes, rebooking and irregular operations",
        "is_historical": False,
    },
    "AI-ADM-Policy-on-GDS-Misuse-eff-01st-Oct23.pdf": {
        "document_title": "Air India ADM Policy - GDS Misuse",
        "audience": "Agent-facing",
        "effective_date": "2023-10-01",
        "topic": "Travel agent and GDS compliance",
        "is_historical": False,
    },
}

SENTENCE_SPLIT = re.compile(r"(?<=[.!?;:])\s+(?=[A-Z0-9(•\-])")
ARTICLE_RE = re.compile(r"\bARTICLE\s+(\d{1,2})\b", re.IGNORECASE)


def clean_page_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.fullmatch(r"(page\s*)?\d{1,3}(\s*(of|/)\s*\d{1,3})?", line, re.IGNORECASE):
            continue  # bare page numbers
        lines.append(line)
    text = " ".join(lines)
    text = text.replace("­", "")              # soft hyphen
    text = re.sub(r"(\w)- (\w)", r"\1\2", text)    # words hyphenated across lines
    text = re.sub(r"[•▪●■]", " • ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str, max_words: int) -> list[str]:
    """Sentence split; very long sentences are cut into max_words windows."""
    out = []
    for sentence in SENTENCE_SPLIT.split(text):
        words = sentence.split()
        while len(words) > max_words:
            out.append(" ".join(words[:max_words]))
            words = words[max_words:]
        if words:
            out.append(" ".join(words))
    return out


def pack_chunks(sentences: list[str], target: int, hard_max: int) -> list[str]:
    chunks, current, count = [], [], 0
    for s in sentences:
        n = len(s.split())
        if current and (count + n > hard_max or count >= target):
            chunks.append(" ".join(current))
            current, count = [], 0
        current.append(s)
        count += n
    if current:
        # merge a tiny tail into the previous chunk on the same page
        if chunks and count < 30 and len(chunks[-1].split()) + count <= hard_max:
            chunks[-1] += " " + " ".join(current)
        else:
            chunks.append(" ".join(current))
    return chunks


def tail_words(text: str, n: int) -> str:
    words = text.split()
    return " ".join(words[-n:]) if len(words) > n else ""


def build(target_words: int, overlap_words: int, hard_max: int) -> pd.DataFrame:
    rows, seen_hashes = [], set()
    chunk_no = 0

    for pdf_name, meta in DOCUMENTS.items():
        pdf_path = PDF_DIR / pdf_name
        if not pdf_path.exists():
            print(f"[skip] {pdf_name} not found")
            continue

        source_txt = pdf_path.with_suffix(".txt").name
        topic = meta["topic"]
        doc = pymupdf.open(pdf_path)

        for page_index, page in enumerate(doc, start=1):
            text = clean_page_text(page.get_text("text"))
            if len(text.split()) < 15:
                continue  # cover pages, blank pages, image-only pages

            # Conditions of Carriage: track the current Article as the topic
            if "Conditions of Carriage" in meta["document_title"]:
                match = ARTICLE_RE.search(text)
                if match:
                    topic = f"Conditions of Carriage - Article {int(match.group(1))}"

            sentences = split_sentences(text, max_words=hard_max - overlap_words)
            previous = ""
            for body in pack_chunks(sentences, target_words, hard_max - overlap_words):
                overlap = tail_words(previous, overlap_words) if previous else ""
                previous = body

                digest = hashlib.md5(body.lower().encode("utf-8")).hexdigest()
                if digest in seen_hashes:
                    continue  # exact duplicate (repeated headers/footers)
                seen_hashes.add(digest)

                chunk_no += 1
                header = (
                    f"Document: {meta['document_title']}\n"
                    f"Audience: {meta['audience']}\n"
                    f"Effective date: {meta['effective_date']}\n"
                    f"Source: {source_txt}\n"
                    f"PDF page: {page_index}\n\n"
                )
                embedded_body = f"... {overlap} {body}" if overlap else body
                word_count = len(embedded_body.split())

                rows.append({
                    "chunk_id": f"AI_CHUNK_{chunk_no:04d}",
                    "document_title": meta["document_title"],
                    "source_file": source_txt,
                    "topic": topic,
                    "audience": meta["audience"],
                    "effective_date": meta["effective_date"],
                    "is_historical": meta["is_historical"],
                    "page_start": page_index,
                    "page_end": page_index,
                    "word_count": word_count,
                    "estimated_tokens": round(word_count * 1.35),
                    "overlap_context": overlap or None,
                    "source_page_reference": f"{source_txt}, PDF page {page_index}",
                    "text": header + embedded_body,
                })

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--target-words", type=int, default=110)
    parser.add_argument("--overlap-words", type=int, default=25)
    parser.add_argument("--max-words", type=int, default=160)
    parser.add_argument("--out", type=Path, default=OUT_CSV)
    args = parser.parse_args()

    df = build(args.target_words, args.overlap_words, args.max_words)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, encoding="utf-8")
    with open(args.out.with_suffix(".jsonl"), "w", encoding="utf-8") as fh:
        for record in df.to_dict(orient="records"):
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(df)} chunks to {args.out}")
    print(df.groupby(["document_title", "audience"]).size().to_string())
    print(f"\nWords per chunk: mean {df.word_count.mean():.0f}, "
          f"min {df.word_count.min()}, max {df.word_count.max()}")


if __name__ == "__main__":
    main()
