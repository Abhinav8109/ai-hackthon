import io
import re
import uuid
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader
import docx
from pptx import Presentation

from backend.database import get_db_connection
from backend.models.schemas import (
    HistoricalDocument,
    CommitmentItem
)

def extract_text_from_file(file_bytes: bytes, filename: str) -> List[Dict[str, str]]:
    """
    Extracts text chunks with exact location identifiers from PDF, DOCX, PPTX, or TXT.
    Returns list of dicts: {"location": str, "text": str}.
    """
    ext = Path(filename).suffix.lower()
    chunks: List[Dict[str, str]] = []

    try:
        if ext == ".pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            for page_num, page in enumerate(reader.pages, start=1):
                txt = page.extract_text() or ""
                if txt.strip():
                    chunks.append({
                        "location": f"Page {page_num}",
                        "text": txt.strip()
                    })
        elif ext in [".docx", ".doc"]:
            doc = docx.Document(io.BytesIO(file_bytes))
            para_num = 1
            current_heading = "General"
            for p in doc.paragraphs:
                txt = p.text.strip()
                if not txt:
                    continue
                if p.style.name.startswith("Heading"):
                    current_heading = txt
                chunks.append({
                    "location": f"{current_heading} (Para {para_num})",
                    "text": txt
                })
                para_num += 1
        elif ext in [".pptx", ".ppt"]:
            prs = Presentation(io.BytesIO(file_bytes))
            for slide_num, slide in enumerate(prs.slides, start=1):
                slide_texts = []
                for shape in slide.shapes:
                    if shape.has_text_frame and shape.text_frame:
                        for paragraph in shape.text_frame.paragraphs:
                            t = paragraph.text.strip()
                            if t:
                                slide_texts.append(t)
                if slide_texts:
                    chunks.append({
                        "location": f"Slide {slide_num}",
                        "text": " \n".join(slide_texts)
                    })
        else: # plain text / markdown
            raw_text = file_bytes.decode("utf-8", errors="replace")
            paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
            for p_num, p in enumerate(paragraphs, start=1):
                chunks.append({
                    "location": f"Section {p_num}",
                    "text": p
                })
    except Exception as e:
        chunks.append({
            "location": "Extract Exception",
            "text": f"Error extracting content: {str(e)}"
        })

    return chunks

def ingest_historical_document(
    file_bytes: bytes,
    filename: str
) -> Tuple[HistoricalDocument, List[Dict[str, str]]]:
    """
    Ingests and indexes historical document, saving chunks into SQLite.
    """
    chunks = extract_text_from_file(file_bytes, filename)
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    ext = Path(filename).suffix.lower()

    # Generate grounded summary
    combined_sample = " ".join([c["text"] for c in chunks[:3]])
    summary = f"Historical {ext.upper()} document with {len(chunks)} extracted sections. Excerpt: {combined_sample[:250]}..."

    doc = HistoricalDocument(
        id=doc_id,
        filename=filename,
        file_type=ext.replace(".", "").upper(),
        upload_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        chunk_count=len(chunks),
        summary=summary,
        page_or_slide_count=len(chunks)
    )

    conn = get_db_connection()
    conn.execute("""
    INSERT OR REPLACE INTO historical_documents (
        id, filename, file_type, upload_date, chunk_count, summary, page_or_slide_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        doc.id, doc.filename, doc.file_type, doc.upload_date,
        doc.chunk_count, doc.summary, doc.page_or_slide_count
    ))

    for c in chunks:
        chunk_id = f"chk_{uuid.uuid4().hex[:10]}"
        conn.execute("""
        INSERT OR REPLACE INTO historical_chunks (
            chunk_id, document_id, document_name, location, text_content
        ) VALUES (?, ?, ?, ?, ?)
        """, (
            chunk_id, doc.id, filename, c["location"], c["text"]
        ))

    conn.commit()
    conn.close()

    return doc, chunks

def search_historical_chunks(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Deterministic ranked search over ingested historical chunks using term frequency scoring.
    Always works locally without external API dependencies.
    """
    query_tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
    if not query_tokens:
        return []

    conn = get_db_connection()
    rows = conn.execute("SELECT chunk_id, document_id, document_name, location, text_content FROM historical_chunks").fetchall()
    conn.close()

    results = []
    for r in rows:
        content_lower = r["text_content"].lower()
        score = 0
        matches = []
        for t in query_tokens:
            count = content_lower.count(t)
            if count > 0:
                score += count * 2 # term frequency weight
                matches.append(t)

        if score > 0:
            results.append({
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "document_name": r["document_name"],
                "location": r["location"],
                "text_content": r["text_content"],
                "matched_tokens": matches,
                "score": score
            })

    # Sort descending by relevance score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]

# --- Commitments Management ---
def list_commitments(status: Optional[str] = None) -> List[CommitmentItem]:
    conn = get_db_connection()
    if status:
        rows = conn.execute("SELECT * FROM commitments WHERE current_status = ?", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM commitments").fetchall()
    conn.close()
    return [CommitmentItem(**dict(r)) for r in rows]

def save_commitment(c: CommitmentItem) -> CommitmentItem:
    conn = get_db_connection()
    conn.execute("""
    INSERT OR REPLACE INTO commitments (
        id, original_wording, source_document, source_location,
        owner, due_date, project_id, expected_outcome,
        current_status, closure_evidence, confidence, review_requirement
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        c.id, c.original_wording, c.source_document, c.source_location,
        c.owner, c.due_date, c.project_id, c.expected_outcome,
        c.current_status, c.closure_evidence, c.confidence, c.review_requirement
    ))
    conn.commit()
    conn.close()
    return c

def extract_commitments_from_text(document_name: str, chunks: List[Dict[str, str]]) -> List[CommitmentItem]:
    """
    Scans text chunks for explicit contractual or QBR commitment phrases.
    """
    commitment_indicators = [
        r"\b(committed to|will deliver|agreed to|scheduled to deploy|action item:|promised to|sla guarantee)\b",
        r"\b(target completion|remediate by|deadline is|pledged to)\b"
    ]
    extracted: List[CommitmentItem] = []

    for c in chunks:
        text = c["text"]
        for pattern in commitment_indicators:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sentence_span = text[:300].strip()
                extracted.append(CommitmentItem(
                    id=f"cmt_{uuid.uuid4().hex[:8]}",
                    original_wording=sentence_span,
                    source_document=document_name,
                    source_location=c["location"],
                    owner="Engineering Lead",
                    due_date="2026-09-30",
                    project_id="core-program",
                    expected_outcome="Delivery per agreed milestone",
                    current_status="requires_human_review",
                    closure_evidence=None,
                    confidence=0.85,
                    review_requirement="Confirm delivery evidence before QBR"
                ))
                break

    return extracted
