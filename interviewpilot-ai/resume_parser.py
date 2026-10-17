"""
Resume Parser Module for InterviewPilot AI.
Extracts structured claims, skills, metrics, and experience from PDF files or raw text.
Uses pypdf and Pydantic for validation.
"""

from typing import List, Dict, Optional
import io
import re
from pydantic import BaseModel, Field

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


class ResumeClaim(BaseModel):
    id: str
    text: str
    category: str = "technical_skill"  # technical_skill, project_metric, architecture, leadership
    keywords: List[str] = Field(default_factory=list)
    confidence: float = 0.85
    verified_status: str = "untested"  # untested, supported, partially_supported, needs_clarification
    interview_evidence: Optional[str] = None


class StructuredResume(BaseModel):
    candidate_name: str = "Candidate"
    email: Optional[str] = None
    title: str = "Software Engineer"
    years_experience: Optional[int] = 3
    skills: Dict[str, List[str]] = Field(default_factory=dict)
    claims: List[ResumeClaim] = Field(default_factory=list)
    raw_text: str = ""


# Tech skill taxonomy for keyword matching
TECH_TAXONOMY = {
    "Languages": ["Python", "JavaScript", "TypeScript", "Go", "Golang", "Java", "C++", "Rust", "SQL"],
    "Frameworks": ["FastAPI", "Django", "Flask", "React", "Next.js", "Node.js", "Express", "Vue"],
    "AI & Data": ["PyTorch", "TensorFlow", "LangChain", "LlamaIndex", "RAG", "LLMs", "Vector DB", "ChromaDB", "Pinecone", "HuggingFace", "Pandas", "NumPy"],
    "Cloud & DevOps": ["AWS", "GCP", "Azure", "Docker", "Kubernetes", "K8s", "CI/CD", "Terraform", "GitHub Actions", "Prometheus"],
    "Databases & Storage": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra", "DynamoDB"],
    "Architecture": ["Microservices", "REST API", "GraphQL", "Distributed Systems", "gRPC", "Kafka", "RabbitMQ", "Caching", "System Design"]
}


def extract_text_from_pdf(pdf_source) -> str:
    """
    Extract raw text from a PDF file (bytes or file-like object).
    """
    if PdfReader is None:
        raise ImportError("pypdf is required to parse PDF resumes. Please install pypdf.")

    if isinstance(pdf_source, bytes):
        reader = PdfReader(io.BytesIO(pdf_source))
    else:
        reader = PdfReader(pdf_source)

    text_parts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)

    return "\n".join(text_parts).strip()


def parse_resume(raw_text: str) -> StructuredResume:
    """
    Parse raw resume text into a StructuredResume with categorized skills and claims.
    """
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    if not lines:
        return StructuredResume(raw_text=raw_text)

    # 1. Candidate Name (heuristic: first non-empty line or name indicator)
    candidate_name = "Candidate"
    first_few = lines[:3]
    for line in first_few:
        if not re.search(r"resume|curriculum|vitae|contact|page", line, re.IGNORECASE) and len(line.split()) <= 4:
            clean = re.sub(r"[^a-zA-Z\s]", "", line).strip()
            if clean and len(clean) > 2:
                candidate_name = clean
                break

    # 2. Email detection
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", raw_text)
    email = email_match.group(0) if email_match else None

    # 3. Estimated Years of Experience
    exp_matches = re.findall(r"(\d+)\+?\s*(?:years|yrs)\s*(?:of\s+)?experience", raw_text, re.IGNORECASE)
    years_experience = int(exp_matches[0]) if exp_matches else 3

    # 4. Extract categorized skills
    categorized_skills: Dict[str, List[str]] = {}
    lower_text = raw_text.lower()
    for category, skill_list in TECH_TAXONOMY.items():
        found = []
        for skill in skill_list:
            pattern = r"\b" + re.escape(skill.lower()) + r"\b"
            if re.search(pattern, lower_text):
                found.append(skill)
        if found:
            categorized_skills[category] = found

    # 5. Extract specific claims and achievements
    # Look for bullet points with action verbs, metrics, scale, architecture
    claims: List[ResumeClaim] = []
    claim_count = 1

    bullet_candidates = re.split(r"\n\s*[•\-\*\u2022\u25cf]\s*|\n(?=[A-Z][a-z]+ed\b)", raw_text)

    for item in bullet_candidates:
        cleaned_item = " ".join(item.split()).strip()
        if len(cleaned_item) < 30 or len(cleaned_item) > 280:
            continue

        # Look for quantifiable claims or architectural statements
        has_metric = bool(re.search(r"\b\d+[\%kKmMbB]?\b|\b(?:latency|scale|optimized|reduced|increased|throughput|concurrency)\b", cleaned_item, re.IGNORECASE))
        has_tech = any(skill.lower() in cleaned_item.lower() for skills in categorized_skills.values() for skill in skills)

        if has_metric or has_tech:
            matched_keywords = []
            for skills in categorized_skills.values():
                for skill in skills:
                    if skill.lower() in cleaned_item.lower() and skill not in matched_keywords:
                        matched_keywords.append(skill)

            cat = "project_metric" if has_metric else "technical_skill"
            if re.search(r"architect|designed|microservices|distributed|system", cleaned_item, re.IGNORECASE):
                cat = "architecture"
            elif re.search(r"lead|managed|mentored|team", cleaned_item, re.IGNORECASE):
                cat = "leadership"

            claims.append(
                ResumeClaim(
                    id=f"claim_{claim_count}",
                    text=cleaned_item,
                    category=cat,
                    keywords=matched_keywords[:4],
                    confidence=0.9 if has_metric else 0.8
                )
            )
            claim_count += 1
            if len(claims) >= 12:
                break

    # If no claims were extracted via bullets, extract sentences with metrics/tech
    if not claims:
        sentences = re.split(r"[.!?]\s+", raw_text)
        for s in sentences:
            s_clean = " ".join(s.split()).strip()
            if 30 <= len(s_clean) <= 220:
                claims.append(
                    ResumeClaim(
                        id=f"claim_{claim_count}",
                        text=s_clean,
                        category="technical_skill",
                        keywords=[w for w in ["Python", "FastAPI", "Docker", "Database"] if w.lower() in s_clean.lower()]
                    )
                )
                claim_count += 1
                if len(claims) >= 6:
                    break

    return StructuredResume(
        candidate_name=candidate_name,
        email=email,
        title="Full-Stack / AI Engineer" if "AI & Data" in categorized_skills else "Software Engineer",
        years_experience=years_experience,
        skills=categorized_skills,
        claims=claims,
        raw_text=raw_text
    )
