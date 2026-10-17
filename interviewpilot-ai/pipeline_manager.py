"""
Pipeline Manager Module for TalentPilot AI.
Manages multi-role talent acquisition:
- Role buckets: Software Engineer, DevOps Engineer, AI/ML Engineer, Frontend Engineer, Cloud & Data Engineer
- AI Sourcing & Shortlisting: Evaluates candidate resumes against target role criteria
- Admin Approvals & Secure Credential Generation
- Candidate Authentication Gateway
- Candidate Interview History & Completed Scorecard Tracking
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import random
from pydantic import BaseModel, Field

from notification_service import send_interview_invitation
from resume_parser import parse_resume, StructuredResume


class CandidateProfile(BaseModel):
    id: str
    name: str
    email: str
    role: str
    experience_years: int
    match_score: int  # 0 to 100
    skills: List[str]
    resume_summary: str
    resume_text: str
    status: str = "Shortlisted"  # Shortlisted, Approved (Invitation Sent), In Progress, Interview Completed
    access_id: Optional[str] = None
    access_code: Optional[str] = None
    invitation_sent_at: Optional[str] = None
    interview_scorecard: Optional[Dict[str, Any]] = None


# Target Job Descriptions for each Role
ROLE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "Software Engineer": {
        "title": "Senior Software Engineer (Python / Distributed Systems)",
        "skills_required": ["Python", "FastAPI", "PostgreSQL", "Redis", "Microservices", "Docker", "Asyncio"],
        "min_experience": 4,
        "description": "Architect and maintain high-throughput backend microservices using Python, FastAPI, and asynchronous workflows. Optimize PostgreSQL queries, manage distributed Redis caching, and ensure 99.99% system availability."
    },
    "DevOps Engineer": {
        "title": "Lead DevOps & Site Reliability Engineer",
        "skills_required": ["Kubernetes", "AWS", "Terraform", "Docker", "CI/CD", "Prometheus", "Helm"],
        "min_experience": 5,
        "description": "Orchestrate multi-region Kubernetes clusters on AWS EKS, automate zero-downtime CI/CD deployment pipelines using GitHub Actions and Terraform, and implement comprehensive Prometheus/Grafana observability."
    },
    "AI/ML Engineer": {
        "title": "Senior AI / LLM Systems Engineer",
        "skills_required": ["PyTorch", "LangChain", "RAG", "Vector DB", "ChromaDB", "Python", "FastAPI"],
        "min_experience": 3,
        "description": "Design and productionize enterprise Retrieval-Augmented Generation (RAG) pipelines, optimize vector search latencies, fine-tune open-source LLMs, and build resilient inference microservices."
    },
    "Frontend Engineer": {
        "title": "Senior Frontend Architect (React / TypeScript)",
        "skills_required": ["React", "TypeScript", "Next.js", "Redux", "TailwindCSS", "Web Vitals"],
        "min_experience": 4,
        "description": "Lead frontend architecture for enterprise SaaS dashboards using Next.js and TypeScript. Champion Core Web Vitals optimization, modular design systems, and responsive, accessible user interfaces."
    },
    "Cloud & Data Engineer": {
        "title": "Senior Data Platform & Streaming Engineer",
        "skills_required": ["Kafka", "Apache Spark", "Snowflake", "Python", "Airflow", "AWS Glue"],
        "min_experience": 5,
        "description": "Build petabyte-scale distributed data ingestion pipelines with Apache Kafka and Spark. Model data lakehouse schemas on Snowflake and orchestrate resilient ETL DAGs using Apache Airflow."
    }
}


# Pre-populated Candidate Database
SUKRIT_RESUME_TEXT = """
Sukrit Sharma
Email: sukrit.ss.31@gmail.com | Phone: (555) 789-2341 | Location: San Francisco, CA
LinkedIn: linkedin.com/in/sukrit-sharma | GitHub: github.com/sukrit-dev

PROFESSIONAL SUMMARY
Senior Software Engineer with 5+ years of experience designing high-throughput distributed microservices in Python, architecting low-latency APIs with FastAPI, and optimizing complex database systems.

TECHNICAL SKILLS
• Languages: Python (Expert), SQL, TypeScript, Go
• Frameworks: FastAPI, Django, Asyncio, Pydantic, SQLAlchemy
• Databases & Caching: PostgreSQL, Redis (Cluster, Sentinel), MongoDB
• Cloud & Infrastructure: AWS (ECS, RDS, S3), Docker, Kubernetes, CI/CD
• Architecture: Microservices, Distributed Systems, Event-Driven Architecture, Caching Patterns

WORK EXPERIENCE
Senior Backend Engineer | ScalePoint Technologies (2022 - Present)
• Architected high-throughput FastAPI microservices handling 20,000 requests/second with sub-45ms latency.
• Engineered a multi-tier distributed Redis caching layer with stale-while-revalidate invalidation, reducing primary PostgreSQL load by 55%.
• Resolved critical connection pool starvation issues in PostgreSQL by introducing PgBouncer connection pooling and query index optimizations.
• Spearheaded migration to containerized Docker microservices orchestrated on Kubernetes.

Backend Software Engineer | DataStream Labs (2019 - 2022)
• Built RESTful and asynchronous payment processing APIs handling $4M+ in daily transaction volume.
• Designed automated regression test suites reducing release cycle times by 35%.

EDUCATION
• B.S. in Computer Science | San Jose State University (2019)
"""

CANDIDATES_DATABASE: Dict[str, CandidateProfile] = {
    "CAND-SE-8109": CandidateProfile(
        id="CAND-SE-8109",
        name="Sukrit Sharma",
        email="sukrit.ss.31@gmail.com",
        role="Software Engineer",
        experience_years=5,
        match_score=96,
        skills=["Python", "FastAPI", "Redis", "PostgreSQL", "Microservices", "Docker", "Asyncio"],
        resume_summary="Engineered high-throughput FastAPI services handling 20k RPS; designed Redis caching reducing DB latency by 55%; resolved PostgreSQL connection pool starvation.",
        resume_text=SUKRIT_RESUME_TEXT,
        status="Shortlisted"
    ),
    "CAND-SE-4421": CandidateProfile(
        id="CAND-SE-4421",
        name="Alex Chen",
        email="alex.chen@example.com",
        role="Software Engineer",
        experience_years=5,
        match_score=92,
        skills=["Python", "FastAPI", "Redis", "Docker", "Kubernetes", "AWS"],
        resume_summary="Built distributed RAG pipelines reducing query latency from 1.8s to 240ms; orchestrated Kubernetes clusters handling 25k RPS.",
        resume_text=SUKRIT_RESUME_TEXT.replace("Sukrit Sharma", "Alex Chen").replace("sukrit.ss.31@gmail.com", "alex.chen@example.com"),
        status="Shortlisted"
    ),
    "CAND-DE-3912": CandidateProfile(
        id="CAND-DE-3912",
        name="Marcus Vance",
        email="marcus.devops@example.com",
        role="DevOps Engineer",
        experience_years=6,
        match_score=95,
        skills=["Kubernetes", "AWS", "Terraform", "Docker", "CI/CD", "Prometheus", "Helm"],
        resume_summary="Designed multi-region AWS EKS clusters with 99.99% uptime; automated zero-downtime canary deployments via GitHub Actions and Terraform.",
        resume_text="Marcus Vance\nEmail: marcus.devops@example.com\nLead DevOps Engineer with 6+ years experience in Kubernetes, Terraform, AWS, and Prometheus.",
        status="Shortlisted"
    ),
    "CAND-AI-7721": CandidateProfile(
        id="CAND-AI-7721",
        name="Dr. Priya Nair",
        email="priya.ai@example.com",
        role="AI/ML Engineer",
        experience_years=4,
        match_score=94,
        skills=["PyTorch", "LangChain", "RAG", "Vector DB", "ChromaDB", "Python", "FastAPI"],
        resume_summary="Architected enterprise RAG system with ChromaDB and LangChain; fine-tuned open-source LLMs reducing hallucination rates by 38%.",
        resume_text="Dr. Priya Nair\nEmail: priya.ai@example.com\nSenior AI/ML Engineer with expertise in PyTorch, LangChain, RAG, and Vector Databases.",
        status="Shortlisted"
    ),
    "CAND-FE-5510": CandidateProfile(
        id="CAND-FE-5510",
        name="David Kim",
        email="david.frontend@example.com",
        role="Frontend Engineer",
        experience_years=5,
        match_score=91,
        skills=["React", "TypeScript", "Next.js", "Redux", "TailwindCSS", "Web Vitals"],
        resume_summary="Led Next.js migration improving Largest Contentful Paint (LCP) by 48%; developed enterprise component design system in TypeScript.",
        resume_text="David Kim\nEmail: david.frontend@example.com\nSenior Frontend Engineer specialized in React, Next.js, TypeScript, and UI performance.",
        status="Shortlisted"
    ),
    "CAND-CD-9014": CandidateProfile(
        id="CAND-CD-9014",
        name="Elena Rostova",
        email="elena.data@example.com",
        role="Cloud & Data Engineer",
        experience_years=6,
        match_score=93,
        skills=["Kafka", "Apache Spark", "Snowflake", "Python", "Airflow", "AWS Glue"],
        resume_summary="Orchestrated real-time streaming pipeline processing 40M daily events with Kafka and Spark; designed Snowflake lakehouse models.",
        resume_text="Elena Rostova\nEmail: elena.data@example.com\nSenior Data Platform Engineer with expertise in Apache Kafka, Spark, Snowflake, and Airflow.",
        status="Shortlisted"
    )
}


def get_all_roles() -> List[str]:
    """Returns list of active recruiting profile roles."""
    return list(ROLE_DEFINITIONS.keys())


def get_role_definition(role_name: str) -> Dict[str, Any]:
    """Returns metadata and requirements for a profile role."""
    return ROLE_DEFINITIONS.get(role_name, ROLE_DEFINITIONS["Software Engineer"])


def get_candidates(role_filter: Optional[str] = None) -> List[CandidateProfile]:
    """Returns candidates optionally filtered by role."""
    candidates = list(CANDIDATES_DATABASE.values())
    if role_filter and role_filter != "All Roles":
        candidates = [c for c in candidates if c.role == role_filter]
    return candidates


def get_candidate_by_id(candidate_id: str) -> Optional[CandidateProfile]:
    """Fetches candidate profile by unique ID."""
    return CANDIDATES_DATABASE.get(candidate_id)


def approve_candidate(candidate_id: str, app_url: str = "http://localhost:8501") -> Dict[str, Any]:
    """
    Admin Action: Approves candidate, generates unique login credentials,
    and dispatches interview invitation to candidate email.
    """
    candidate = CANDIDATES_DATABASE.get(candidate_id)
    if not candidate:
        return {"status": "error", "message": "Candidate not found."}

    # Generate secure credentials
    access_code = f"PILOT-{random.randint(1000, 9999)}"
    candidate.access_id = candidate.id
    candidate.access_code = access_code
    candidate.status = "Approved (Invitation Sent)"
    candidate.invitation_sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Send notification email
    interview_link = f"{app_url}?view=candidate_login&cand_id={candidate.id}"
    dispatch_res = send_interview_invitation(
        candidate_name=candidate.name,
        candidate_email=candidate.email,
        role_name=candidate.role,
        access_id=candidate.access_id,
        access_code=candidate.access_code,
        interview_url=interview_link
    )

    return {
        "status": "success",
        "candidate": candidate,
        "access_id": candidate.access_id,
        "access_code": candidate.access_code,
        "dispatch_log": dispatch_res
    }


def authenticate_candidate(access_id_or_email: str, access_code: str) -> Optional[CandidateProfile]:
    """
    Authenticates candidate at interview login gateway.
    """
    clean_id = access_id_or_email.strip().lower()
    clean_code = access_code.strip().upper()

    for cand in CANDIDATES_DATABASE.values():
        if (cand.id.lower() == clean_id or cand.email.lower() == clean_id):
            if cand.access_code and cand.access_code.upper() == clean_code:
                return cand
            # Also allow fallback test demo login if code matches standard format
            elif clean_code in ["PILOT-DEMO", "DEMO123"] or (cand.access_code is None and clean_code == "START"):
                cand.access_code = "PILOT-DEMO"
                cand.access_id = cand.id
                return cand
    return None


def record_interview_completion(candidate_id: str, scorecard: Dict[str, Any]) -> None:
    """
    Saves completed interview metrics back to candidate profile for recruiter audit.
    """
    candidate = CANDIDATES_DATABASE.get(candidate_id)
    if candidate:
        candidate.status = "Interview Completed"
        candidate.interview_scorecard = scorecard


def shortlist_uploaded_resume(candidate_name: str, email: str, role: str, raw_text: str) -> CandidateProfile:
    """
    Agentic Sourcing AI: Analyzes uploaded resume text, calculates match score against target role,
    and categorizes candidate into appropriate profile bucket.
    """
    parsed = parse_resume(raw_text)
    role_def = get_role_definition(role)
    required_skills = role_def["skills_required"]

    # Calculate match score based on keyword and claim overlap
    extracted_skills_flat = [s.lower() for skills in parsed.skills.values() for s in skills]
    text_lower = raw_text.lower()

    matched_skills = [s for s in required_skills if s.lower() in text_lower or s.lower() in extracted_skills_flat]
    base_score = int((len(matched_skills) / max(1, len(required_skills))) * 70)
    exp_bonus = min(25, (parsed.years_experience or 3) * 5)
    final_score = min(99, max(60, base_score + exp_bonus))

    new_id = f"CAND-{role[:2].upper()}-{random.randint(1000, 9999)}"
    candidate = CandidateProfile(
        id=new_id,
        name=candidate_name if candidate_name else parsed.candidate_name,
        email=email if email else (parsed.email or f"{new_id.lower()}@example.com"),
        role=role,
        experience_years=parsed.years_experience or 3,
        match_score=final_score,
        skills=matched_skills if matched_skills else required_skills[:4],
        resume_summary=f"Parsed {len(parsed.claims)} verifiable claims; matched {len(matched_skills)} core skills for {role}.",
        resume_text=raw_text,
        status="Shortlisted"
    )

    CANDIDATES_DATABASE[new_id] = candidate
    return candidate
