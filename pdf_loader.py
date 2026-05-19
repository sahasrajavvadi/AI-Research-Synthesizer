"""
PDF Text Extraction Module
Handles extraction of text from uploaded PDF files
"""

import io
import os
import re
from typing import List, Tuple


def extract_text_from_pdf(pdf_file) -> Tuple[str, str]:
    """
    Extract text content from a PDF file.
    Tries pdfplumber first (better quality), falls back to PyPDF2.

    Args:
        pdf_file: Open binary file object

    Returns:
        Tuple of (full_text, filename)
    """
    filename = os.path.basename(pdf_file.name)
    file_bytes = pdf_file.read()
    text = ""

    # ── Try pdfplumber first (much better at extracting columnar / complex layouts) ──
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text
        if text.strip():
            print(f"[PDF_LOADER] pdfplumber: extracted {len(text)} chars from '{filename}'")
            return clean_text(text), filename
        print(f"[PDF_LOADER] pdfplumber returned empty text for '{filename}', trying PyPDF2")
    except ImportError:
        print("[PDF_LOADER] pdfplumber not installed — falling back to PyPDF2")
    except Exception as e:
        print(f"[PDF_LOADER] pdfplumber error on '{filename}': {e} — trying PyPDF2")

    # ── Fallback: PyPDF2 ──
    try:
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            if page_text.strip():
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page_text
        print(f"[PDF_LOADER] PyPDF2: extracted {len(text)} chars from '{filename}'")
    except Exception as e:
        raise Exception(f"Cannot extract text from '{filename}': {e}")

    if not text.strip():
        print(f"[PDF_LOADER] WARNING: No readable text found in '{filename}'. "
              "The PDF may be image-based (scanned). OCR is required for such files.")

    return clean_text(text), filename


def clean_text(text: str) -> str:
    """
    Clean and normalize extracted PDF text.
    Fixes:
    - Broken spacing between words
    - Hyphenated line breaks
    - Missing spaces between lowercase-uppercase
    - Collapsed words
    - Excess whitespace
    """

    # 1️⃣ Fix hyphen line breaks (e.g., "comparisontai- lored" → "comparisontailored")
    text = re.sub(r'-\s*\n\s*', '', text)

    # 2️⃣ Replace newlines inside paragraphs with space
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

    # 3️⃣ Fix lowercase-uppercase word joins (e.g., "bridgethisgapByProviding")
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

    # 4️⃣ Fix common missing spaces after punctuation
    text = re.sub(r'([.,;:])([A-Za-z])', r'\1 \2', text)

    # 5️⃣ Fix words stuck together due to PDF extraction
    # Example: "Wereleasethemodelsandcode"
    # Insert space before long lowercase sequences followed by uppercase
    text = re.sub(r'([a-z]{4,})([A-Z])', r'\1 \2', text)

    # 6️⃣ Collapse multiple spaces
    text = re.sub(r'[ \t]+', ' ', text)

    # 7️⃣ Normalize multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 8️⃣ Strip each line
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if len(stripped) > 10:   # keep meaningful lines
            lines.append(stripped)

    return '\n'.join(lines)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping word-based chunks.
    Larger chunks (500 words) so more document content is retained per chunk
    and full answers are less likely to be cut off.

    Args:
        text:       The full extracted text
        chunk_size: Words per chunk (default 500 for better coverage)
        overlap:    Overlapping words between consecutive chunks

    Returns:
        List of non-empty text chunks
    """
    print(f"[PDF_LOADER] Chunking — chunk_size={chunk_size}, overlap={overlap}")
    words = text.split()
    total_words = len(words)
    print(f"[PDF_LOADER] Total words to chunk: {total_words}")

    if total_words == 0:
        return []

    chunks = []
    start = 0
    while start < total_words:
        end = min(start + chunk_size, total_words)
        chunk = " ".join(words[start:end])
        # Only keep chunks with at least 30 words (avoids tiny tail chunks)
        if len(chunk.split()) >= 30:
            chunks.append(chunk)
        if end == total_words:
            break
        start += chunk_size - overlap

    print(f"[PDF_LOADER] Created {len(chunks)} chunks")
    return chunks


def prepare_chunks_with_metadata(pdf_files: List) -> List[dict]:
    """
    Process multiple PDFs and return a flat list of chunk dicts.

    Each dict has:
        content  : the text of the chunk
        source   : filename (basename only) — used as the doc identifier
        chunk_id : position within this document

    Args:
        pdf_files: List of open binary file objects

    Returns:
        List of chunk metadata dicts across ALL uploaded PDFs
    """
    all_chunks = []

    for pdf_file in pdf_files:
        print(f"[PDF_LOADER] ── Processing file: {pdf_file.name} ──")
        try:
            text, filename = extract_text_from_pdf(pdf_file)
        except Exception as e:
            print(f"[PDF_LOADER] ERROR — skipping '{pdf_file.name}': {e}")
            continue

        if not text.strip():
            print(f"[PDF_LOADER] WARNING — '{filename}' produced no text; skipping.")
            continue

        chunks = chunk_text(text)
        print(f"[PDF_LOADER] '{filename}' → {len(chunks)} chunks")

        for idx, chunk in enumerate(chunks):
            all_chunks.append({
                "content":  chunk,
                "source":   filename,   # ← basename only (e.g. "paper.pdf")
                "chunk_id": idx,
            })

    print(f"[PDF_LOADER] Total chunks across all PDFs: {len(all_chunks)}")
    return all_chunks