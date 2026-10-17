import os
import pytest
from pptx import Presentation
from backend.services.presentation import generate_qbr_presentation
from backend.models.schemas import PresentationConfig
from backend.database import init_db, get_db_connection

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_presentation_generation_and_validation():
    config = PresentationConfig(
        reporting_period="2026-Q3",
        program_name="Cloud Platform Optimization",
        customer_name="Global Enterprise Inc"
    )
    result = generate_qbr_presentation(config)

    assert result["verified"] is True
    assert result["slide_count"] >= 5
    assert os.path.exists(result["filepath"])
    assert result["filename"].endswith(".pptx")

    # Reopen directly to verify python-pptx integrity
    prs = Presentation(result["filepath"])
    assert len(prs.slides) == result["slide_count"]

    # Verify database entry
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM reports WHERE report_id = ?", (result["report_id"],)).fetchone()
    assert row is not None
    assert row["format"] == "pptx"
    conn.close()
