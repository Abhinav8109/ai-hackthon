"""
Database Module for TalentPilot AI.
Provides SQLite persistence for the complete enterprise recruitment workflow:
- Jobs & Job Descriptions
- Candidates & Shortlisting references
- Interview Plans (8-10 questions)
- Interview Invitations & Cryptographic Tokens
- Interview Sessions & Active Progress
- Questions, Answers & Transcripts (Turn-by-turn)
- Evaluation Scorecards & Verbatim Evidence
- Consistency Findings
- Email Notifications & Delivery Status
- Audit Events & Recruiter Decisions
"""

import sqlite3
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "talentpilot.db")


def get_db_connection() -> sqlite3.Connection:
    """Create a thread-safe connection to SQLite database."""
    conn = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initialize relational database tables and indexes."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Jobs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            department TEXT NOT NULL,
            description TEXT NOT NULL,
            skills_required TEXT NOT NULL, -- JSON array
            min_experience INTEGER DEFAULT 3,
            created_at TEXT NOT NULL
        );
        """)

        # 2. Candidates Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            experience_years INTEGER NOT NULL,
            match_score INTEGER NOT NULL, -- 0-100
            skills TEXT NOT NULL, -- JSON array
            resume_summary TEXT NOT NULL,
            resume_text TEXT NOT NULL,
            shortlist_status TEXT NOT NULL DEFAULT 'SHORTLISTED',
            workflow_status TEXT NOT NULL DEFAULT 'SHORTLISTED',
            -- Workflow states: SHORTLISTED, FIRST_ROUND_APPROVED, INVITATION_PENDING, INVITED,
            -- INVITATION_FAILED, IN_PROGRESS, EVALUATION_PENDING, COMPLETED,
            -- SECOND_ROUND_APPROVED, ON_HOLD, HUMAN_REVIEW_REQUIRED
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );
        """)

        # 3. Interview Plans Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_plans (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            questions TEXT NOT NULL, -- JSON array of 8-10 questions
            created_at TEXT NOT NULL,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );
        """)

        # 4. Interview Sessions & Invitations Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            token_expires_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'INVITED', -- INVITED, IN_PROGRESS, COMPLETED, EXPIRED
            current_question_index INTEGER DEFAULT 0,
            active_followup_question TEXT,
            started_at TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );
        """)

        # 5. Interview Q&A Turns Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_qa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question_id INTEGER NOT NULL,
            competency TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            question_text TEXT NOT NULL,
            targeted_claim TEXT,
            candidate_answer TEXT NOT NULL,
            followup_question TEXT,
            followup_answer TEXT,
            score INTEGER,
            completeness REAL,
            evidence_quote TEXT,
            rubric_match TEXT,
            strengths TEXT,
            gaps TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id)
        );
        """)

        # 6. Evaluation Scorecards Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_scorecards (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL UNIQUE,
            candidate_id TEXT NOT NULL,
            overall_score REAL NOT NULL,
            technical_score REAL NOT NULL,
            problem_solving_score REAL NOT NULL,
            communication_score REAL NOT NULL,
            job_fit_score REAL NOT NULL,
            recommendation TEXT NOT NULL, -- ADVANCE, HOLD, REJECT
            human_review_flag INTEGER DEFAULT 0, -- 1 if human review required
            strengths TEXT NOT NULL,
            gaps TEXT NOT NULL,
            candidate_feedback TEXT NOT NULL,
            consistency_findings TEXT NOT NULL, -- JSON array
            transcript_summary TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(id),
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        );
        """)

        # 7. Email Notifications Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_notifications (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            notification_type TEXT NOT NULL, -- FIRST_ROUND_INVITATION, SECOND_ROUND_SELECTION
            recipient_email TEXT NOT NULL,
            recipient_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            body_text TEXT NOT NULL,
            body_html TEXT NOT NULL,
            delivery_status TEXT NOT NULL, -- QUEUED, ACCEPTED, DELIVERED, FAILED
            provider_reference TEXT,
            error_details TEXT,
            attempts INTEGER DEFAULT 1,
            sent_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id)
        );
        """)

        # 8. Audit Events Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL
        );
        """)

        # Indexes for fast lookup
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(workflow_status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON interview_sessions(token);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_candidate ON interview_sessions(candidate_id);")

        conn.commit()


def seed_database_if_empty() -> None:
    """Pre-populates realistic enterprise recruitment data if tables are empty."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs;")
        if cursor.fetchone()[0] > 0:
            return  # Already seeded

        now = datetime.now(timezone.utc).isoformat()

        # Seed 5 Enterprise Roles
        jobs = [
            (
                "JOB-SE-01",
                "Senior Software Engineer",
                "Backend Platform & Infrastructure",
                "Architect and maintain high-throughput backend microservices using Python, FastAPI, and asynchronous workflows. Optimize PostgreSQL queries, manage distributed Redis caching, and ensure 99.99% system availability.",
                json.dumps(["Python", "FastAPI", "PostgreSQL", "Redis", "Microservices", "Docker", "Asyncio"]),
                4,
                now
            ),
            (
                "JOB-DE-02",
                "Lead DevOps & SRE",
                "Cloud & Reliability",
                "Orchestrate multi-region Kubernetes clusters on AWS EKS, automate zero-downtime CI/CD deployment pipelines using GitHub Actions and Terraform, and implement comprehensive Prometheus/Grafana observability.",
                json.dumps(["Kubernetes", "AWS", "Terraform", "Docker", "CI/CD", "Prometheus", "Helm"]),
                5,
                now
            ),
            (
                "JOB-AI-03",
                "Senior AI Systems Engineer",
                "Machine Learning & AI",
                "Design and productionize enterprise Retrieval-Augmented Generation (RAG) pipelines, optimize vector search latencies, fine-tune open-source LLMs, and build resilient inference microservices.",
                json.dumps(["PyTorch", "LangChain", "RAG", "Vector DB", "ChromaDB", "Python", "FastAPI"]),
                3,
                now
            ),
            (
                "JOB-FE-04",
                "Senior Frontend Architect",
                "Product Engineering",
                "Lead frontend architecture for enterprise SaaS dashboards using Next.js and TypeScript. Champion Core Web Vitals optimization, modular design systems, and responsive, accessible user interfaces.",
                json.dumps(["React", "TypeScript", "Next.js", "Redux", "TailwindCSS", "Web Vitals"]),
                4,
                now
            ),
            (
                "JOB-CD-05",
                "Senior Data Platform Engineer",
                "Data & Analytics",
                "Build petabyte-scale distributed data ingestion pipelines with Apache Kafka and Spark. Model data lakehouse schemas on Snowflake and orchestrate resilient ETL DAGs using Apache Airflow.",
                json.dumps(["Kafka", "Apache Spark", "Snowflake", "Python", "Airflow", "AWS Glue"]),
                5,
                now
            )
        ]
        cursor.executemany("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?)", jobs)

        # Seed Shortlisted Candidates from Use Case 1 (including Sukrit Sharma)
        sukrit_resume = """Sukrit Sharma
Email: sukrit.ss.31@gmail.com | Location: San Francisco, CA | Phone: (555) 789-2341
PROFESSIONAL SUMMARY
Senior Software Engineer with 5+ years of experience designing high-throughput distributed microservices in Python, architecting low-latency APIs with FastAPI, and optimizing complex database systems.
TECHNICAL SKILLS
• Languages: Python (Expert), SQL, TypeScript, Go
• Frameworks: FastAPI, Django, Asyncio, Pydantic, SQLAlchemy
• Databases & Caching: PostgreSQL, Redis (Cluster, Sentinel), MongoDB
• Cloud & Infrastructure: AWS (ECS, RDS, S3), Docker, Kubernetes, CI/CD
WORK EXPERIENCE
Senior Backend Engineer | ScalePoint Technologies (2022 - Present)
• Architected high-throughput FastAPI microservices handling 20,000 requests/second with sub-45ms latency.
• Engineered a multi-tier distributed Redis caching layer with stale-while-revalidate invalidation, reducing primary PostgreSQL load by 55%.
• Resolved critical connection pool starvation issues in PostgreSQL by introducing PgBouncer connection pooling and query index optimizations.
• Spearheaded migration to containerized Docker microservices orchestrated on Kubernetes."""

        candidates = [
            (
                "CAND-SE-8109",
                "JOB-SE-01",
                "Sukrit Sharma",
                "sukrit.ss.31@gmail.com",
                "Backend Platform & Infrastructure",
                5,
                96,
                json.dumps(["Python", "FastAPI", "Redis", "PostgreSQL", "Microservices", "Docker", "Asyncio"]),
                "Engineered high-throughput FastAPI services handling 20k RPS; designed Redis caching reducing DB latency by 55%; resolved PostgreSQL connection pool starvation.",
                sukrit_resume,
                "SHORTLISTED",
                "SHORTLISTED",
                now,
                now
            ),
            (
                "CAND-SE-4421",
                "JOB-SE-01",
                "Alex Chen",
                "alex.chen@example.com",
                "Backend Platform & Infrastructure",
                5,
                92,
                json.dumps(["Python", "FastAPI", "Redis", "Docker", "Kubernetes", "AWS"]),
                "Built distributed RAG pipelines reducing query latency from 1.8s to 240ms; orchestrated Kubernetes clusters handling 25k RPS.",
                sukrit_resume.replace("Sukrit Sharma", "Alex Chen").replace("sukrit.ss.31@gmail.com", "alex.chen@example.com"),
                "SHORTLISTED",
                "SHORTLISTED",
                now,
                now
            ),
            (
                "CAND-DE-3912",
                "JOB-DE-02",
                "Marcus Vance",
                "marcus.devops@example.com",
                "Cloud & Reliability",
                6,
                95,
                json.dumps(["Kubernetes", "AWS", "Terraform", "Docker", "CI/CD", "Prometheus", "Helm"]),
                "Designed multi-region AWS EKS clusters with 99.99% uptime; automated zero-downtime canary deployments via GitHub Actions and Terraform.",
                "Marcus Vance\nEmail: marcus.devops@example.com\nLead DevOps Engineer with 6+ years experience in Kubernetes, Terraform, AWS, and Prometheus.",
                "SHORTLISTED",
                "SHORTLISTED",
                now,
                now
            ),
            (
                "CAND-AI-7721",
                "JOB-AI-03",
                "Dr. Priya Nair",
                "priya.ai@example.com",
                "Machine Learning & AI",
                4,
                94,
                json.dumps(["PyTorch", "LangChain", "RAG", "Vector DB", "ChromaDB", "Python", "FastAPI"]),
                "Architected enterprise RAG system with ChromaDB and LangChain; fine-tuned open-source LLMs reducing hallucination rates by 38%.",
                "Dr. Priya Nair\nEmail: priya.ai@example.com\nSenior AI/ML Engineer with expertise in PyTorch, LangChain, RAG, and Vector Databases.",
                "SHORTLISTED",
                "SHORTLISTED",
                now,
                now
            ),
            (
                "CAND-FE-5510",
                "JOB-FE-04",
                "David Kim",
                "david.frontend@example.com",
                "Product Engineering",
                5,
                91,
                json.dumps(["React", "TypeScript", "Next.js", "Redux", "TailwindCSS", "Web Vitals"]),
                "Led Next.js migration improving Largest Contentful Paint (LCP) by 48%; developed enterprise component design system in TypeScript.",
                "David Kim\nEmail: david.frontend@example.com\nSenior Frontend Engineer specialized in React, Next.js, TypeScript, and UI performance.",
                "SHORTLISTED",
                "SHORTLISTED",
                now,
                now
            ),
            (
                "CAND-CD-9014",
                "JOB-CD-05",
                "Elena Rostova",
                "elena.data@example.com",
                "Data & Analytics",
                6,
                93,
                json.dumps(["Kafka", "Apache Spark", "Snowflake", "Python", "Airflow", "AWS Glue"]),
                "Orchestrated real-time streaming pipeline processing 40M daily events with Kafka and Spark; designed Snowflake lakehouse models.",
                "Elena Rostova\nEmail: elena.data@example.com\nSenior Data Platform Engineer with expertise in Apache Kafka, Spark, Snowflake, and Airflow.",
                "SHORTLISTED",
                "SHORTLISTED",
                now,
                now
            )
        ]
        cursor.executemany("INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", candidates)
        conn.commit()


# Helper query methods
def get_all_jobs() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY title ASC;").fetchall()
        return [dict(r) for r in rows]


def get_job_by_id(job_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?;", (job_id,)).fetchone()
        return dict(row) if row else None


def get_candidates_list(status_filter: Optional[str] = None, job_filter: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    query = """
    SELECT c.*, j.title as job_title, j.department as job_department,
           s.token, s.status as session_status, s.token_expires_at,
           n.delivery_status as last_email_status, n.sent_at as last_email_time,
           sc.overall_score, sc.recommendation, sc.human_review_flag
    FROM candidates c
    JOIN jobs j ON c.job_id = j.id
    LEFT JOIN interview_sessions s ON c.id = s.candidate_id
    LEFT JOIN (
        SELECT candidate_id, delivery_status, sent_at,
               ROW_NUMBER() OVER (PARTITION BY candidate_id ORDER BY created_at DESC) as rn
        FROM email_notifications
    ) n ON c.id = n.candidate_id AND n.rn = 1
    LEFT JOIN evaluation_scorecards sc ON s.id = sc.session_id
    WHERE 1=1
    """
    params = []
    if status_filter and status_filter != "ALL":
        query += " AND c.workflow_status = ?"
        params.append(status_filter)
    if job_filter and job_filter != "ALL":
        query += " AND c.job_id = ?"
        params.append(job_filter)
    if search:
        query += " AND (c.name LIKE ? OR c.email LIKE ?)"
        s = f"%{search.strip()}%"
        params.extend([s, s])

    query += " ORDER BY c.match_score DESC, c.created_at DESC;"

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["skills"] = json.loads(d["skills"]) if isinstance(d["skills"], str) else d["skills"]
            result.append(d)
        return result


def get_candidate_details(candidate_id: str) -> Optional[Dict[str, Any]]:
    query = """
    SELECT c.*, j.title as job_title, j.department as job_department, j.description as job_description,
           s.id as session_id, s.token, s.status as session_status, s.token_expires_at, s.started_at, s.completed_at
    FROM candidates c
    JOIN jobs j ON c.job_id = j.id
    LEFT JOIN interview_sessions s ON c.id = s.candidate_id
    WHERE c.id = ?;
    """
    with get_db_connection() as conn:
        row = conn.execute(query, (candidate_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["skills"] = json.loads(d["skills"]) if isinstance(d["skills"], str) else d["skills"]
        return d


def get_session_by_token(token: str) -> Optional[Dict[str, Any]]:
    query = """
    SELECT s.*, c.name as candidate_name, c.email as candidate_email, c.resume_text, c.skills as candidate_skills,
           c.workflow_status as candidate_status,
           j.title as job_title, j.department as job_department, j.description as job_description,
           p.questions as plan_questions
    FROM interview_sessions s
    JOIN candidates c ON s.candidate_id = c.id
    JOIN jobs j ON s.job_id = j.id
    LEFT JOIN interview_plans p ON s.candidate_id = p.candidate_id
    WHERE s.token = ?;
    """
    with get_db_connection() as conn:
        row = conn.execute(query, (token.strip(),)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["candidate_skills"] = json.loads(d["candidate_skills"]) if isinstance(d["candidate_skills"], str) else d["candidate_skills"]
        d["plan_questions"] = json.loads(d["plan_questions"]) if d["plan_questions"] else []
        return d


def get_scorecard_by_candidate_id(candidate_id: str) -> Optional[Dict[str, Any]]:
    query = """
    SELECT sc.*, c.name as candidate_name, c.email as candidate_email, c.workflow_status,
           j.title as job_title, j.department as job_department, s.completed_at as interview_completed_at
    FROM evaluation_scorecards sc
    JOIN candidates c ON sc.candidate_id = c.id
    JOIN jobs j ON c.job_id = j.id
    JOIN interview_sessions s ON sc.session_id = s.id
    WHERE sc.candidate_id = ?
    ORDER BY sc.created_at DESC LIMIT 1;
    """
    with get_db_connection() as conn:
        row = conn.execute(query, (candidate_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["consistency_findings"] = json.loads(d["consistency_findings"]) if isinstance(d["consistency_findings"], str) else []
        return d


def get_qa_turns_by_session_id(session_id: str) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM interview_qa WHERE session_id = ? ORDER BY question_id ASC;", (session_id,)).fetchall()
        return [dict(r) for r in rows]


def get_all_email_logs() -> List[Dict[str, Any]]:
    query = """
    SELECT n.*, c.name as candidate_name, c.id as candidate_id, j.title as job_title
    FROM email_notifications n
    JOIN candidates c ON n.candidate_id = c.id
    JOIN jobs j ON c.job_id = j.id
    ORDER BY n.created_at DESC;
    """
    with get_db_connection() as conn:
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]


def get_audit_events() -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 100;").fetchall()
        return [dict(r) for r in rows]


def log_audit_event(entity_type: str, entity_id: str, action: str, actor: str, details: str = "") -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO audit_events (entity_type, entity_id, action, actor, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (entity_type, entity_id, action, actor, details, now)
        )
        conn.commit()


def insert_or_replace_candidate(
    candidate_id: str,
    job_id: str,
    name: str,
    email: str,
    department: str,
    experience_years: int,
    match_score: int,
    skills: List[str],
    resume_summary: str,
    resume_text: str,
    shortlist_status: str = "SHORTLISTED",
    workflow_status: str = "SHORTLISTED"
) -> Dict[str, Any]:
    """Inserts a new candidate profile or updates an existing one by email."""
    now = datetime.now(timezone.utc).isoformat()
    skills_json = json.dumps(skills) if isinstance(skills, list) else skills
    with get_db_connection() as conn:
        existing = conn.execute("SELECT id FROM candidates WHERE email = ?;", (email.strip(),)).fetchone()
        if existing:
            actual_id = existing[0]
            conn.execute("""
            UPDATE candidates SET
                job_id = ?, name = ?, department = ?, experience_years = ?,
                match_score = ?, skills = ?, resume_summary = ?, resume_text = ?,
                shortlist_status = ?, workflow_status = ?, updated_at = ?
            WHERE id = ?;
            """, (
                job_id, name, department, experience_years,
                match_score, skills_json, resume_summary, resume_text,
                shortlist_status, workflow_status, now, actual_id
            ))
            conn.commit()
            log_audit_event("candidate", actual_id, "UPDATED_RESUME", "Admin", f"Updated resume for {name} ({email})")
            return {"id": actual_id, "action": "updated"}
        else:
            conn.execute("""
            INSERT INTO candidates (
                id, job_id, name, email, department, experience_years,
                match_score, skills, resume_summary, resume_text,
                shortlist_status, workflow_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                candidate_id, job_id, name, email.strip(), department, experience_years,
                match_score, skills_json, resume_summary, resume_text,
                shortlist_status, workflow_status, now, now
            ))
            conn.commit()
            log_audit_event("candidate", candidate_id, "CREATED_SHORTLISTED", "Admin", f"Ingested and shortlisted {name} ({email}) under {job_id}")
            return {"id": candidate_id, "action": "created"}

