import pytest
from backend.services.data_ingestion import parse_and_validate_file, save_canonical_records_to_db
from backend.database import init_db, get_db_connection

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_parse_valid_csv():
    csv_data = """KPI,Actual,Target,Unit,Category,Direction
Availability,99.4,99.9,%,SLA,higher
MTTR,45,60,minutes,Operational,lower
CSAT,4.8,4.5,score,Customer,higher
"""
    report, records = parse_and_validate_file(
        file_bytes=csv_data.encode("utf-8"),
        filename="test_q3_kpis.csv",
        reporting_period="2026-Q3"
    )

    assert report.total_rows == 3
    assert report.valid_rows == 3
    assert report.invalid_rows == 0
    assert report.resolution_status == "passed"
    assert len(records) == 3
    
    # Check first record mapping & lineage
    rec = records[0]
    assert rec.metric_name == "Availability"
    assert rec.actual_value == 99.4
    assert rec.target_value == 99.9
    assert rec.unit == "%"
    assert rec.direction_of_improvement == "higher_is_better"
    assert rec.source_file == "test_q3_kpis.csv"
    assert rec.source_row == 2

def test_parse_with_invalid_and_out_of_bounds():
    csv_data = """metric,actual,target,unit
InvalidNumber,NOT_A_NUM,99.0,%
OverHundredPct,135.0,99.0,%
DuplicateMetric,50,50,%
DuplicateMetric,60,50,%
"""
    report, records = parse_and_validate_file(
        file_bytes=csv_data.encode("utf-8"),
        filename="messy_data.csv",
        reporting_period="2026-Q3"
    )

    assert report.total_rows == 4
    assert report.valid_rows == 3 # 1 failed numeric, 3 parsed with warnings
    assert report.invalid_rows == 1
    assert report.duplicate_rows == 1
    assert any(w.issue_type == "percentage_out_of_bounds" for w in report.warnings)
    assert any(e.issue_type == "invalid_numeric" for e in report.errors)

def test_save_to_database_and_query():
    csv_data = "metric,actual,target,unit\nTestSLA,99.1,99.5,%\n"
    report, records = parse_and_validate_file(
        file_bytes=csv_data.encode("utf-8"),
        filename="db_test.csv",
        reporting_period="2026-Q3"
    )
    save_canonical_records_to_db(records, report)

    conn = get_db_connection()
    row = conn.execute("SELECT * FROM canonical_kpis WHERE metric_name = 'TestSLA'").fetchone()
    assert row is not None
    assert row["actual_value"] == 99.1
    assert row["target_value"] == 99.5
    assert row["source_file"] == "db_test.csv"
    conn.close()
