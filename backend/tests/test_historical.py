import pytest
from backend.services.historical import (
    ingest_historical_document,
    search_historical_chunks,
    extract_commitments_from_text,
    save_commitment,
    list_commitments
)
from backend.database import init_db

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_ingest_and_search_historical_text():
    sample_doc = """Executive Q2 Summary:
In Q2 we committed to upgrading the database cluster by August 15.

SLA Review:
Core latency met the 120ms target, but weekend backups caused an availability dip.
We agreed to deploy automated failover in Q3.
"""
    doc, chunks = ingest_historical_document(sample_doc.encode("utf-8"), "q2_review.txt")
    assert doc.chunk_count >= 2
    assert doc.filename == "q2_review.txt"

    # Search for "failover"
    results = search_historical_chunks("failover")
    assert len(results) >= 1
    assert "failover" in results[0]["matched_tokens"]
    assert "Slide" in results[0]["location"] or "Section" in results[0]["location"]

def test_extract_and_save_commitments():
    chunks = [
        {"location": "Section 1", "text": "The team committed to upgrading the database cluster by August 15."},
        {"location": "Section 2", "text": "General status overview was discussed without changes."}
    ]
    extracted = extract_commitments_from_text("minutes.txt", chunks)
    assert len(extracted) == 1
    assert "committed to" in extracted[0].original_wording.lower()

    save_commitment(extracted[0])
    all_cmt = list_commitments()
    assert any(c.id == extracted[0].id for c in all_cmt)
