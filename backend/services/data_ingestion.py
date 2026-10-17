import io
import csv
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import openpyxl

from backend.config import settings
from backend.models.schemas import (
    CanonicalKPIRecord,
    ValidationReport,
    ValidationIssue
)
from backend.database import get_db_connection

# Canonical mapping dictionaries for automatic column matching
COLUMN_SYNONYMS = {
    "metric_name": ["metric", "kpi", "kpi_name", "indicator", "metric_name", "measure"],
    "metric_category": ["category", "kpi_category", "type", "domain", "workstream_category"],
    "actual_value": ["actual", "actual_value", "value", "current", "result", "performance"],
    "target_value": ["target", "target_value", "goal", "sla_target", "threshold"],
    "unit": ["unit", "uom", "measurement_unit", "scale"],
    "reporting_period": ["quarter", "period", "reporting_period", "qtr", "date_range"],
    "project": ["project", "project_name", "initiative", "app"],
    "program": ["program", "portfolio", "track"],
    "workstream": ["workstream", "team", "service", "stream"],
    "direction_of_improvement": ["direction", "direction_of_improvement", "trend_target", "improvement_direction"]
}

def auto_detect_mapping(columns: List[str]) -> Dict[str, str]:
    """
    Intelligently maps uploaded spreadsheet/csv column names to canonical KPI schema fields.
    """
    mapping = {}
    normalized_cols = {col.lower().strip().replace(" ", "_"): col for col in columns}
    
    for canonical_field, synonyms in COLUMN_SYNONYMS.items():
        for syn in synonyms:
            if syn in normalized_cols:
                mapping[canonical_field] = normalized_cols[syn]
                break
                
    return mapping

def parse_and_validate_file(
    file_bytes: bytes,
    filename: str,
    reporting_period: str = "2026-Q3",
    custom_mapping: Optional[Dict[str, str]] = None
) -> Tuple[ValidationReport, List[CanonicalKPIRecord]]:
    """
    Parses CSV/XLSX/JSON and validates rows against business rules and canonical schema.
    Tracks precise data lineage down to row number and file name.
    """
    dataset_id = f"ds_{uuid.uuid4().hex[:8]}"
    ext = Path(filename).suffix.lower()
    
    records: List[CanonicalKPIRecord] = []
    warnings: List[ValidationIssue] = []
    errors: List[ValidationIssue] = []
    total_rows = 0
    duplicate_rows = 0
    
    df: Optional[pd.DataFrame] = None
    sheet_name = "Sheet1"
    
    try:
        if ext == ".csv":
            df = pd.read_csv(io.BytesIO(file_bytes))
        elif ext in [".xlsx", ".xls"]:
            excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
            sheet_name = excel_file.sheet_names[0]
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
        elif ext == ".json":
            data = json.loads(file_bytes.decode("utf-8"))
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict) and "records" in data:
                df = pd.DataFrame(data["records"])
            else:
                df = pd.DataFrame([data])
        else:
            errors.append(ValidationIssue(
                issue_type="unsupported_format",
                message=f"File extension '{ext}' is not supported for structured KPI ingestion.",
                severity="error"
            ))
            return ValidationReport(
                dataset_id=dataset_id,
                filename=filename,
                total_rows=0,
                valid_rows=0,
                invalid_rows=0,
                duplicate_rows=0,
                warnings=warnings,
                errors=errors,
                resolution_status="failed"
            ), []
    except Exception as e:
        errors.append(ValidationIssue(
            issue_type="parse_failure",
            message=f"Failed to parse file: {str(e)}",
            severity="error"
        ))
        return ValidationReport(
            dataset_id=dataset_id,
            filename=filename,
            total_rows=0,
            valid_rows=0,
            invalid_rows=0,
            duplicate_rows=0,
            warnings=warnings,
            errors=errors,
            resolution_status="failed"
        ), []

    if df is None or df.empty:
        errors.append(ValidationIssue(
            issue_type="empty_dataset",
            message="The uploaded dataset contains zero rows.",
            severity="error"
        ))
        return ValidationReport(
            dataset_id=dataset_id,
            filename=filename,
            total_rows=0,
            valid_rows=0,
            invalid_rows=0,
            duplicate_rows=0,
            warnings=warnings,
            errors=errors,
            resolution_status="failed"
        ), []

    total_rows = len(df)
    mapping = custom_mapping or auto_detect_mapping(list(df.columns))

    # Verify minimum required columns
    metric_col = mapping.get("metric_name")
    actual_col = mapping.get("actual_value")
    target_col = mapping.get("target_value")

    if not metric_col or not actual_col:
        errors.append(ValidationIssue(
            issue_type="missing_canonical_mapping",
            message="Could not map required columns: 'metric_name' and 'actual_value'.",
            severity="error"
        ))
        return ValidationReport(
            dataset_id=dataset_id,
            filename=filename,
            total_rows=total_rows,
            valid_rows=0,
            invalid_rows=total_rows,
            duplicate_rows=0,
            warnings=warnings,
            errors=errors,
            resolution_status="failed"
        ), []

    seen_metrics = set()

    for idx, row in df.iterrows():
        row_num = int(idx) + 2 # Accounting for 1-based index and header row
        metric = str(row.get(metric_col, "")).strip() if pd.notna(row.get(metric_col)) else ""

        if not metric:
            errors.append(ValidationIssue(
                row_index=row_num,
                column=metric_col,
                issue_type="missing_metric_name",
                message=f"Row {row_num}: Missing metric name.",
                severity="error"
            ))
            continue

        if metric in seen_metrics:
            duplicate_rows += 1
            warnings.append(ValidationIssue(
                row_index=row_num,
                column=metric_col,
                issue_type="duplicate_metric",
                message=f"Row {row_num}: Duplicate metric '{metric}' in the same reporting period.",
                severity="warning"
            ))
        seen_metrics.add(metric)

        # Actual value validation
        raw_actual = row.get(actual_col)
        try:
            if pd.isna(raw_actual) or raw_actual == "":
                raise ValueError("Value is empty")
            actual_val = float(raw_actual)
        except Exception:
            errors.append(ValidationIssue(
                row_index=row_num,
                column=actual_col,
                issue_type="invalid_numeric",
                message=f"Row {row_num}: Invalid actual numeric value '{raw_actual}'.",
                severity="error"
            ))
            continue

        # Target value validation
        raw_target = row.get(target_col) if target_col else None
        try:
            if pd.isna(raw_target) or raw_target is None or raw_target == "":
                target_val = 0.0
                warnings.append(ValidationIssue(
                    row_index=row_num,
                    column=target_col or "target_value",
                    issue_type="missing_target",
                    message=f"Row {row_num}: Target value missing; defaulted to 0.0.",
                    severity="warning"
                ))
            else:
                target_val = float(raw_target)
        except Exception:
            warnings.append(ValidationIssue(
                row_index=row_num,
                column=target_col,
                issue_type="invalid_target_numeric",
                message=f"Row {row_num}: Invalid target '{raw_target}'; defaulted to 0.0.",
                severity="warning"
            ))
            target_val = 0.0

        # Unit & category
        unit_col = mapping.get("unit")
        unit = str(row.get(unit_col, "%")).strip() if unit_col and pd.notna(row.get(unit_col)) else "%"

        cat_col = mapping.get("metric_category")
        category = str(row.get(cat_col, "Operational")).strip() if cat_col and pd.notna(row.get(cat_col)) else "Operational"

        dir_col = mapping.get("direction_of_improvement")
        direction_val = str(row.get(dir_col, "higher_is_better")).strip().lower() if dir_col and pd.notna(row.get(dir_col)) else "higher_is_better"
        direction = "lower_is_better" if "lower" in direction_val or "decrease" in direction_val else "higher_is_better"

        # Percentage validation checks
        if unit == "%":
            if actual_val < 0 or actual_val > 100:
                warnings.append(ValidationIssue(
                    row_index=row_num,
                    column=actual_col,
                    issue_type="percentage_out_of_bounds",
                    message=f"Row {row_num}: Percentage {actual_val}% is outside typical 0-100% range.",
                    severity="warning"
                ))

        proj_col = mapping.get("project")
        project = str(row.get(proj_col, "Core Program")).strip() if proj_col and pd.notna(row.get(proj_col)) else "Core Program"

        prog_col = mapping.get("program")
        program = str(row.get(prog_col, "Enterprise Governance")).strip() if prog_col and pd.notna(row.get(prog_col)) else "Enterprise Governance"

        ws_col = mapping.get("workstream")
        workstream = str(row.get(ws_col, "Operations")).strip() if ws_col and pd.notna(row.get(ws_col)) else "Operations"

        rec = CanonicalKPIRecord(
            record_id=f"rec_{uuid.uuid4().hex[:8]}",
            reporting_period=reporting_period,
            project=project,
            program=program,
            workstream=workstream,
            metric_name=metric,
            metric_category=category,
            actual_value=actual_val,
            target_value=target_val,
            unit=unit,
            direction_of_improvement=direction,
            currency="USD",
            source_file=filename,
            worksheet_or_table=sheet_name,
            source_row=row_num,
            source_cell=f"R{row_num}C1",
            data_quality_status="warning" if any(w.row_index == row_num for w in warnings) else "valid"
        )
        records.append(rec)

    valid_count = len(records)
    invalid_count = total_rows - valid_count
    
    if len(errors) > 0 and valid_count == 0:
        resolution = "failed"
    elif len(warnings) > 0 or len(errors) > 0:
        resolution = "warnings_pending"
    else:
        resolution = "passed"

    report = ValidationReport(
        dataset_id=dataset_id,
        filename=filename,
        total_rows=total_rows,
        valid_rows=valid_count,
        invalid_rows=invalid_count,
        duplicate_rows=duplicate_rows,
        warnings=warnings,
        errors=errors,
        resolution_status=resolution
    )

    return report, records

def save_canonical_records_to_db(records: List[CanonicalKPIRecord], report: ValidationReport):
    """
    Saves validated records and the validation report to SQLite database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Save report
    cursor.execute("""
    INSERT OR REPLACE INTO validation_reports (
        dataset_id, filename, total_rows, valid_rows, invalid_rows, duplicate_rows,
        warnings_json, errors_json, resolution_status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        report.dataset_id,
        report.filename,
        report.total_rows,
        report.valid_rows,
        report.invalid_rows,
        report.duplicate_rows,
        json.dumps([w.model_dump() for w in report.warnings]),
        json.dumps([e.model_dump() for e in report.errors]),
        report.resolution_status
    ))

    # Save canonical records
    for rec in records:
        cursor.execute("""
        INSERT OR REPLACE INTO canonical_kpis (
            record_id, reporting_period, project, program, workstream,
            metric_name, metric_category, actual_value, target_value, unit,
            direction_of_improvement, currency, source_file, worksheet_or_table,
            source_row, source_cell, timestamp, data_quality_status, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rec.record_id,
            rec.reporting_period,
            rec.project,
            rec.program,
            rec.workstream,
            rec.metric_name,
            rec.metric_category,
            rec.actual_value,
            rec.target_value,
            rec.unit,
            rec.direction_of_improvement,
            rec.currency,
            rec.source_file,
            rec.worksheet_or_table,
            rec.source_row,
            rec.source_cell,
            rec.timestamp.isoformat(),
            rec.data_quality_status,
            rec.notes
        ))

    conn.commit()
    conn.close()
