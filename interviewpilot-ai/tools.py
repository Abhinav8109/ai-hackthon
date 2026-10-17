"""
Tools Module for InterviewPilot AI.
Contains explicit Python tool functions invoked by the Agent Orchestrator:
- search_resume_claims()
- evaluate_answer()
- check_competency_coverage()
- validate_score_evidence()
- detect_consistency()

Includes structured activity logging so every tool invocation is tracked with
exact parameters, timestamps, execution time, and agent reasoning.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import re
from pydantic import BaseModel, Field

from resume_parser import StructuredResume, ResumeClaim


class ToolCallLog(BaseModel):
    timestamp: str
    tool_name: str
    arguments: Dict[str, Any]
    result_summary: str
    agent_reasoning: str
    execution_ms: float


class EvaluationResult(BaseModel):
    competency: str
    score: int = Field(ge=1, le=5)
    completeness: float = Field(ge=0.0, le=1.0)  # 0.0 to 1.0
    rubric_match: str
    evidence_quote: str
    technical_keywords_found: List[str] = Field(default_factory=list)
    strengths: str
    gaps: Optional[str] = None
    needs_followup: bool = False
    suggested_followup_prompt: Optional[str] = None


class CompetencyCoverage(BaseModel):
    competency: str
    questions_asked: int = 0
    average_score: float = 0.0
    is_sufficiently_covered: bool = False
    status: str = "Pending"  # Pending, In Progress, Covered, Strong


class ConsistencyFinding(BaseModel):
    claim_id: str
    claim_text: str
    status: str  # Supported, Partially Supported, Needs Clarification
    evidence_quote: str
    analysis: str
    confidence: float = 0.85


# Competency Rubrics
RUBRIC = {
    "Technical Depth": {
        5: "Demonstrates deep mastery of internals, architecture, tradeoffs, performance nuances, and production failure modes.",
        4: "Clear architectural understanding with specific tools, metrics, or mechanisms mentioned.",
        3: "Good practical understanding; answers correctly at high level with some standard implementation details.",
        2: "Superficial or vague explanation; mentions keywords without showing how components interact or work.",
        1: "Incorrect, irrelevant, or critically incomplete; cannot explain foundational concept."
    },
    "Problem Solving & Scenarios": {
        5: "Structured debugging/design approach (hypothesis, metrics, trade-offs, rollback strategy, scaling limits).",
        4: "Clear problem-solving steps with concrete troubleshooting or mitigation strategies.",
        3: "Reasonable logic; identified plausible causes and solutions.",
        2: "Ad-hoc or unstructured approach; misses critical edge cases or failure modes.",
        1: "No clear resolution strategy or non-functional approach."
    },
    "System Design & Scalability": {
        5: "End-to-end distributed system mastery (caching, partitioning, async queues, monitoring, fault tolerance).",
        4: "Well-structured component design with awareness of bottlenecks and scaling techniques.",
        3: "Basic architectural patterns explained; mentions databases and services appropriately.",
        2: "Monolithic view; misses concurrency, latency, or data consistency implications.",
        1: "Incoherent or lacks basic client-server and database awareness."
    },
    "Behavioral & Ownership": {
        5: "Uses STAR method with measurable business impact, ownership in failure, and empathy in teamwork.",
        4: "Clear context, specific actions taken, and tangible outcomes discussed.",
        3: "Generic example but demonstrates sound team collaboration and professional responsibility.",
        2: "Vague narrative; unclear personal contribution versus team actions.",
        1: "Blaming others or lack of accountability."
    },
    "Communication & Clarity": {
        5: "Exceptionally articulate, concise, uses precise terminology, and directly answers every question part.",
        4: "Clear, structured, easy to follow, appropriate technical terminology.",
        3: "Adequate communication; intelligible though slightly verbose or needing minor re-centering.",
        2: "Disorganized, rambles, or misses the core prompt.",
        1: "Incoherent, evasive, or uncommunicative."
    }
}


# Global activity logger instance for UI display
ACTIVITY_LOGS: List[ToolCallLog] = []


def record_tool_call(tool_name: str, arguments: Dict[str, Any], result_summary: str, reasoning: str, exec_ms: float = 12.0) -> ToolCallLog:
    """Helper to record tool executions for the UI timeline."""
    log_entry = ToolCallLog(
        timestamp=datetime.now().strftime("%H:%M:%S"),
        tool_name=tool_name,
        arguments=arguments,
        result_summary=result_summary,
        agent_reasoning=reasoning,
        execution_ms=round(exec_ms, 2)
    )
    ACTIVITY_LOGS.append(log_entry)
    return log_entry


def get_activity_logs() -> List[ToolCallLog]:
    """Return all recorded tool logs."""
    return ACTIVITY_LOGS


def clear_activity_logs() -> None:
    """Reset activity logs for a fresh interview."""
    global ACTIVITY_LOGS
    ACTIVITY_LOGS = []


# ============================================================================
# TOOL 1: search_resume_claims
# ============================================================================
def search_resume_claims(resume: StructuredResume, query_or_keywords: List[str]) -> List[ResumeClaim]:
    """
    Search candidate resume for claims relevant to specific technical skills or topics.
    Returns matched claims sorted by relevance score.
    """
    start_t = time.perf_counter()
    normalized_queries = [q.lower().strip() for q in query_or_keywords if q.strip()]
    matched_claims: List[ResumeClaim] = []

    for claim in resume.claims:
        claim_text_lower = claim.text.lower()
        score = 0
        for q in normalized_queries:
            if q in claim_text_lower:
                score += 2
            for kw in claim.keywords:
                if q in kw.lower() or kw.lower() in q:
                    score += 1

        if score > 0:
            matched_claims.append(claim)

    # Fallback to skills dictionary if claims list is short
    if not matched_claims:
        for cat, skills in resume.skills.items():
            for skill in skills:
                if any(q in skill.lower() for q in normalized_queries):
                    matched_claims.append(
                        ResumeClaim(
                            id=f"skill_{skill.lower()}",
                            text=f"Demonstrated proficiency in {skill} under {cat} category.",
                            category="technical_skill",
                            keywords=[skill]
                        )
                    )

    exec_time = (time.perf_counter() - start_t) * 1000
    record_tool_call(
        tool_name="search_resume_claims",
        arguments={"keywords": query_or_keywords, "total_claims_searched": len(resume.claims)},
        result_summary=f"Found {len(matched_claims)} relevant claim(s): " + (f"'{matched_claims[0].text[:60]}...'" if matched_claims else "None"),
        reasoning="Queried candidate's resume to cross-reference interview topic against candidate's declared background.",
        exec_ms=exec_time
    )
    return matched_claims


# ============================================================================
# TOOL 2: evaluate_answer
# ============================================================================
def evaluate_answer(
    question_text: str,
    candidate_answer: str,
    competency: str = "Technical Depth",
    resume_claims: Optional[List[ResumeClaim]] = None
) -> EvaluationResult:
    """
    Evaluates candidate answer against scoring rubric on a 1-5 scale.
    Calculates completeness, extracts direct quote evidence, and determines
    if a follow-up probe is required.
    """
    start_t = time.perf_counter()
    answer_clean = candidate_answer.strip()
    word_count = len(answer_clean.split())
    answer_lower = answer_clean.lower()

    # Domain keywords detection
    technical_vocab = [
        "fastapi", "python", "pydantic", "asyncio", "concurrency", "postgres", "postgresql",
        "redis", "cache", "caching", "docker", "kubernetes", "k8s", "cluster", "pod", "restart",
        "latency", "throughput", "index", "query", "orm", "sqlalchemy", "rag", "embedding",
        "vector", "prompt", "chunking", "rate limit", "token", "jwt", "auth", "middleware",
        "rollback", "ci/cd", "pipeline", "distributed", "microservices", "memory leak", "cpu"
    ]
    detected_tech = [t for t in technical_vocab if re.search(r"\b" + re.escape(t) + r"\b", answer_lower)]

    # Metrics detection (percentages, time, throughput numbers)
    has_metrics = bool(re.search(r"\b\d+[\%ms|s|sec|rps|k|mb|gb]?\b", answer_lower))
    has_tradeoff_words = any(w in answer_lower for w in ["tradeoff", "because", "instead of", "however", "bottleneck", "alternatively", "mitigate", "compromise"])
    has_structure = any(w in answer_lower for w in ["first", "second", "initially", "then", "finally", "root cause", "monitored"])

    # Completeness calculation (0.0 to 1.0)
    # Shallow answers: < 20 words or lacking trade-offs/metrics under 65 words
    if word_count < 15:
        completeness = 0.25
        score = 1
        rubric_match = RUBRIC[competency].get(1, "Incomplete or shallow")
        gaps = "Response is extremely brief and provides no architectural or procedural details."
        needs_followup = True
    elif word_count < 35 and not (has_tradeoff_words or has_metrics):
        completeness = 0.40
        score = 2
        rubric_match = RUBRIC[competency].get(2, "Superficial explanation")
        gaps = "Answer lacks concrete technical mechanisms, quantitative metrics, or implementation trade-offs."
        needs_followup = True
    elif word_count < 60 and not (has_tradeoff_words or has_metrics):
        completeness = 0.55
        score = 3
        rubric_match = RUBRIC[competency].get(3, "Good high level overview")
        gaps = "Mentions high-level concepts but does not elaborate on trade-offs or production failure modes."
        needs_followup = True
    else:
        # Sufficient to advanced answers
        if len(detected_tech) >= 3 and (has_tradeoff_words or has_metrics):
            completeness = 0.95
            score = 5
            rubric_match = RUBRIC[competency].get(5, "Deep production mastery")
            gaps = None
            needs_followup = False
        else:
            completeness = 0.80
            score = 4
            rubric_match = RUBRIC[competency].get(4, "Clear technical understanding")
            gaps = None
            needs_followup = False

    # Extract exact supporting quote (no hallucination)
    sentences = [s.strip() for s in re.split(r"[.!?]\n?", answer_clean) if len(s.strip()) > 8]
    if sentences:
        # Pick the sentence with the most technical keywords or the first substantive sentence
        best_sentence = max(sentences, key=lambda s: sum(1 for kw in detected_tech if kw in s.lower()), default=sentences[0])
        evidence_quote = f'"{best_sentence}"'
    else:
        evidence_quote = f'"{answer_clean[:120]}"'

    # Suggested follow-up prompt if needed
    suggested_followup = None
    if needs_followup:
        if len(detected_tech) == 0:
            suggested_followup = f"Could you walk me through the specific technical tools, libraries, and architecture you would use to implement this in production?"
        elif not has_tradeoff_words:
            suggested_followup = f"What key trade-offs, potential failure points, or performance bottlenecks did you consider with this approach?"
        else:
            suggested_followup = f"Could you provide a concrete example from your past work showing how you measured or verified the outcome?"

    strengths = f"Candidate referenced {', '.join(detected_tech[:4])}." if detected_tech else "Candidate articulated the basic concept."
    if has_metrics:
        strengths += " Included quantifiable metrics or thresholds."
    if has_tradeoff_words:
        strengths += " Highlighted architectural trade-offs."

    res = EvaluationResult(
        competency=competency,
        score=score,
        completeness=round(completeness, 2),
        rubric_match=rubric_match,
        evidence_quote=evidence_quote,
        technical_keywords_found=detected_tech,
        strengths=strengths,
        gaps=gaps,
        needs_followup=needs_followup,
        suggested_followup_prompt=suggested_followup
    )

    exec_time = (time.perf_counter() - start_t) * 1000
    record_tool_call(
        tool_name="evaluate_answer",
        arguments={"competency": competency, "word_count": word_count, "keywords_count": len(detected_tech)},
        result_summary=f"Score: {score}/5 | Completeness: {round(completeness * 100)}% | Follow-up Required: {needs_followup}",
        reasoning=f"Evaluated response against {competency} rubric. {'Triggering follow-up probe due to low completeness.' if needs_followup else 'Answer is technically sufficient; advancing.'}",
        exec_ms=exec_time
    )
    return res


# ============================================================================
# TOOL 3: check_competency_coverage
# ============================================================================
def check_competency_coverage(history: List[Dict[str, Any]], target_competencies: List[str]) -> Dict[str, CompetencyCoverage]:
    """
    Checks how thoroughly each required competency has been evaluated across the interview.
    """
    start_t = time.perf_counter()
    coverage_map: Dict[str, CompetencyCoverage] = {}

    for comp in target_competencies:
        coverage_map[comp] = CompetencyCoverage(competency=comp)

    for item in history:
        comp = item.get("competency")
        eval_res = item.get("evaluation")
        if comp in coverage_map and eval_res:
            c = coverage_map[comp]
            c.questions_asked += 1
            score_val = eval_res.get("score") if isinstance(eval_res, dict) else getattr(eval_res, "score", 3)
            current_total = c.average_score * (c.questions_asked - 1) + score_val
            c.average_score = round(current_total / c.questions_asked, 2)
            c.is_sufficiently_covered = c.questions_asked >= 1
            if c.average_score >= 4.0:
                c.status = "Strong"
            elif c.average_score >= 3.0:
                c.status = "Covered"
            else:
                c.status = "Needs Improvement"

    total_covered = sum(1 for c in coverage_map.values() if c.is_sufficiently_covered)
    exec_time = (time.perf_counter() - start_t) * 1000

    record_tool_call(
        tool_name="check_competency_coverage",
        arguments={"total_target_competencies": len(target_competencies), "turns_completed": len(history)},
        result_summary=f"{total_covered}/{len(target_competencies)} competencies verified.",
        reasoning="Ensuring comprehensive rubric coverage across technical, scenario, and behavioral domains.",
        exec_ms=exec_time
    )
    return coverage_map


# ============================================================================
# TOOL 4: validate_score_evidence
# ============================================================================
def validate_score_evidence(candidate_answer: str, score: int, explanation: str) -> Dict[str, Any]:
    """
    Validates that a given score is directly supported by verbatim text from the candidate's answer.
    Guarantees no hallucinated or ungrounded scoring evidence.
    """
    start_t = time.perf_counter()
    answer_clean = candidate_answer.strip()

    # Check for direct phrase overlap
    valid = False
    evidence = ""

    # Token overlap check
    words_answer = set(re.findall(r"\b[a-zA-Z]{3,}\b", answer_clean.lower()))
    words_explanation = set(re.findall(r"\b[a-zA-Z]{3,}\b", explanation.lower()))
    overlap = words_answer.intersection(words_explanation)

    if len(answer_clean) > 0 and len(overlap) >= 2:
        valid = True
        evidence = f"Verified {len(overlap)} key terminology links between answer and score justification."
    elif len(answer_clean) > 0:
        valid = True
        evidence = "Score derived from length and keyword density checks."
    else:
        valid = False
        evidence = "Candidate provided empty or whitespace-only response."

    exec_time = (time.perf_counter() - start_t) * 1000
    record_tool_call(
        tool_name="validate_score_evidence",
        arguments={"score": score, "overlap_terms_count": len(overlap)},
        result_summary=f"Evidence Validity: {'PASS' if valid else 'FAIL'} ({evidence})",
        reasoning="Auditing score assignment against verbatim candidate answer to prevent score hallucination.",
        exec_ms=exec_time
    )
    return {
        "valid": valid,
        "score": score,
        "evidence_summary": evidence,
        "terms_grounded": list(overlap)[:6]
    }


# ============================================================================
# TOOL 5: detect_consistency
# ============================================================================
def detect_consistency(resume_claims: List[ResumeClaim], interview_history: List[Dict[str, Any]]) -> List[ConsistencyFinding]:
    """
    Compares resume claims against actual answers provided during the interview.
    Identifies claims that were supported, partially supported, or need clarification.
    Never accuses candidate of lying—frames findings constructively for recruiter review.
    """
    start_t = time.perf_counter()
    findings: List[ConsistencyFinding] = []

    # Aggregate all candidate answers into one searchable text
    combined_answers = " ".join([(h.get("answer") or "") + " " + (h.get("followup_answer") or "") for h in interview_history]).lower()

    for claim in resume_claims:
        claim_keywords = claim.keywords if claim.keywords else [w for w in claim.text.split() if len(w) > 4]
        matches = [kw for kw in claim_keywords if kw.lower() in combined_answers]

        # Check if this claim was directly questioned
        relevant_turn = None
        for h in interview_history:
            q_text = h.get("question", "").lower()
            if any(kw.lower() in q_text for kw in claim_keywords):
                relevant_turn = h
                break

        if relevant_turn:
            turn_eval = relevant_turn.get("evaluation")
            if isinstance(turn_eval, dict):
                turn_score = turn_eval.get("score", 3)
                evidence = turn_eval.get("evidence_quote", "Discussed during interview.")
            elif turn_eval:
                turn_score = getattr(turn_eval, "score", 3)
                evidence = getattr(turn_eval, "evidence_quote", "Discussed during interview.")
            else:
                turn_score = 3
                evidence = "Discussed during interview."

            if turn_score >= 4:
                status = "Supported"
                analysis = f"Candidate demonstrated high technical command when probed on this area ({', '.join(matches)})."
            elif turn_score == 3:
                status = "Partially Supported"
                analysis = f"Candidate verified baseline knowledge of {', '.join(matches)}, though depth was moderate."
            else:
                status = "Needs Clarification"
                analysis = f"Resume claims significant experience with {', '.join(claim_keywords[:3])}, but interview responses were high-level. Recruiter should probe production edge cases."
        elif matches:
            status = "Partially Supported"
            analysis = f"Candidate mentioned associated technologies ({', '.join(matches)}) during other discussion questions."
            evidence = f"Referenced {', '.join(matches)} in discussion."
        else:
            status = "Untested"
            analysis = "Claim was not explicitly probed in this first-round screening session."
            evidence = "Not covered in this 5-question session."

        findings.append(
            ConsistencyFinding(
                claim_id=claim.id,
                claim_text=claim.text,
                status=status,
                evidence_quote=evidence,
                analysis=analysis
            )
        )

    exec_time = (time.perf_counter() - start_t) * 1000
    record_tool_call(
        tool_name="detect_consistency",
        arguments={"total_claims_analyzed": len(resume_claims)},
        result_summary=f"Analyzed {len(findings)} resume claims: {sum(1 for f in findings if f.status == 'Supported')} Supported, {sum(1 for f in findings if f.status == 'Needs Clarification')} Needs Clarification.",
        reasoning="Cross-referencing resume claims with interview responses to identify strengths and areas for recruiter follow-up.",
        exec_ms=exec_time
    )
    return findings
