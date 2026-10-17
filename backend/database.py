import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.config import settings

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(settings.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Canonical KPIs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS canonical_kpis (
        record_id TEXT PRIMARY KEY,
        reporting_period TEXT NOT NULL,
        project TEXT NOT NULL,
        program TEXT NOT NULL,
        workstream TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        metric_category TEXT NOT NULL,
        actual_value REAL NOT NULL,
        target_value REAL NOT NULL,
        unit TEXT NOT NULL,
        direction_of_improvement TEXT NOT NULL,
        currency TEXT,
        source_file TEXT NOT NULL,
        worksheet_or_table TEXT,
        source_row INTEGER,
        source_cell TEXT,
        timestamp TEXT NOT NULL,
        data_quality_status TEXT NOT NULL,
        notes TEXT
    )
    """)

    # Validation reports table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS validation_reports (
        dataset_id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        total_rows INTEGER NOT NULL,
        valid_rows INTEGER NOT NULL,
        invalid_rows INTEGER NOT NULL,
        duplicate_rows INTEGER NOT NULL,
        warnings_json TEXT NOT NULL,
        errors_json TEXT NOT NULL,
        resolution_status TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # Projects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        program TEXT NOT NULL,
        sponsor TEXT NOT NULL,
        owner TEXT NOT NULL,
        health TEXT NOT NULL,
        delivery_confidence REAL NOT NULL,
        approved_budget REAL NOT NULL,
        actual_spend REAL NOT NULL,
        reporting_period TEXT NOT NULL,
        key_updates TEXT NOT NULL
    )
    """)

    # Milestones table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS milestones (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        project_name TEXT NOT NULL,
        title TEXT NOT NULL,
        planned_date TEXT NOT NULL,
        actual_or_forecast_date TEXT NOT NULL,
        completion_pct REAL NOT NULL,
        status TEXT NOT NULL,
        owner TEXT NOT NULL,
        criticality TEXT NOT NULL,
        dependencies_json TEXT NOT NULL,
        recovery_plan TEXT,
        customer_dependency INTEGER DEFAULT 0,
        escalation_status TEXT
    )
    """)

    # RAID table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raid_items (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        impact INTEGER NOT NULL,
        likelihood INTEGER NOT NULL,
        score INTEGER NOT NULL,
        severity TEXT NOT NULL,
        owner TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT NOT NULL,
        mitigation TEXT NOT NULL,
        contingency TEXT,
        project_id TEXT NOT NULL,
        related_milestone_id TEXT,
        source_reference TEXT
    )
    """)

    # Actions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS action_items (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        owner TEXT NOT NULL,
        priority TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT NOT NULL,
        related_qbr TEXT NOT NULL,
        linked_risk_id TEXT,
        dependencies_json TEXT NOT NULL,
        acceptance_criteria TEXT NOT NULL,
        closure_evidence TEXT,
        closure_date TEXT,
        is_proposal INTEGER DEFAULT 0
    )
    """)

    # Decisions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decision_items (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        options_considered_json TEXT NOT NULL,
        selected_decision TEXT NOT NULL,
        rationale TEXT NOT NULL,
        decision_owner TEXT NOT NULL,
        decision_date TEXT NOT NULL,
        status TEXT NOT NULL,
        dependencies_json TEXT NOT NULL,
        follow_up_actions_json TEXT NOT NULL,
        customer_ask INTEGER DEFAULT 0
    )
    """)

    # Historical Documents & Chunks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historical_documents (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        upload_date TEXT NOT NULL,
        chunk_count INTEGER NOT NULL,
        summary TEXT NOT NULL,
        page_or_slide_count INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historical_chunks (
        chunk_id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        document_name TEXT NOT NULL,
        location TEXT NOT NULL,
        text_content TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES historical_documents(id)
    )
    """)

    # Commitments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS commitments (
        id TEXT PRIMARY KEY,
        original_wording TEXT NOT NULL,
        source_document TEXT NOT NULL,
        source_location TEXT NOT NULL,
        owner TEXT NOT NULL,
        due_date TEXT NOT NULL,
        project_id TEXT NOT NULL,
        expected_outcome TEXT NOT NULL,
        current_status TEXT NOT NULL,
        closure_evidence TEXT,
        confidence REAL NOT NULL,
        review_requirement TEXT NOT NULL
    )
    """)

    # Customer QA Items table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS qa_items (
        id TEXT PRIMARY KEY,
        question TEXT NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        why_asked TEXT NOT NULL,
        supporting_kpi_evidence TEXT NOT NULL,
        linked_commitment TEXT,
        recommended_answer TEXT NOT NULL,
        diplomatic_phrasing TEXT NOT NULL,
        evidence_coverage TEXT NOT NULL,
        user_edited_answer TEXT,
        approved INTEGER DEFAULT 0,
        rehearsal_notes TEXT
    )
    """)

    # Agent runs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_runs (
        run_id TEXT PRIMARY KEY,
        reporting_period TEXT NOT NULL,
        status TEXT NOT NULL,
        current_stage TEXT NOT NULL,
        stages_json TEXT NOT NULL,
        tool_calls_json TEXT NOT NULL,
        executive_narrative_json TEXT,
        critic_notes_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Scenarios table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scenarios (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        inputs_json TEXT NOT NULL,
        results_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # Reports table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        report_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        reporting_period TEXT NOT NULL,
        format TEXT NOT NULL,
        filepath TEXT NOT NULL,
        created_at TEXT NOT NULL,
        metadata_json TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
