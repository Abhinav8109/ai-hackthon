"""
Agent Orchestrator Module for InterviewPilot AI.
Controls the agentic interview lifecycle:
1. Generates resume-aware, JD-aligned interview questions
2. Orchestrates tool calls (search_resume_claims, evaluate_answer, validate_score_evidence, check_competency_coverage, detect_consistency)
3. Evaluates answers adaptively and decides whether to trigger a targeted follow-up probe
4. Manages difficulty stepping and state transitions
5. Compiles final scorecard data with human-in-the-loop recruiter safeguards.
"""

from typing import List, Dict, Any, Optional
import json
import os
from pydantic import BaseModel, Field

from resume_parser import StructuredResume, ResumeClaim
from tools import (
    search_resume_claims,
    evaluate_answer,
    check_competency_coverage,
    validate_score_evidence,
    detect_consistency,
    record_tool_call,
    EvaluationResult,
    ConsistencyFinding,
    RUBRIC
)


class Question(BaseModel):
    id: int
    competency: str
    text: str
    targeted_resume_claim: Optional[str] = None
    jd_requirement: str
    difficulty: str = "standard"  # foundational, standard, advanced
    evaluation_criteria: str


class TurnRecord(BaseModel):
    question_id: int
    competency: str
    question: str
    targeted_resume_claim: Optional[str] = None
    answer: str
    evaluation: EvaluationResult
    followup_question: Optional[str] = None
    followup_answer: Optional[str] = None
    followup_evaluation: Optional[EvaluationResult] = None
    final_score: int
    difficulty: str = "standard"


class InterviewState(BaseModel):
    candidate_name: str = "Candidate"
    job_title: str = "Software Engineer"
    questions: List[Question] = Field(default_factory=list)
    current_index: int = 0
    history: List[TurnRecord] = Field(default_factory=list)
    status: str = "READY"  # READY, IN_PROGRESS, AWAITING_FOLLOWUP, COMPLETED
    current_difficulty: str = "standard"
    active_followup: Optional[str] = None
    resume: Optional[StructuredResume] = None
    job_description: str = ""
    consistency_findings: List[ConsistencyFinding] = Field(default_factory=list)


TARGET_COMPETENCIES = [
    "Technical Depth",
    "Problem Solving & Scenarios",
    "System Design & Scalability",
    "Behavioral & Ownership",
    "Communication & Clarity"
]


class InterviewPilotAgent:
    """
    Agentic Orchestrator for automated first-round screening interviews.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.state = InterviewState()

    def plan_interview(self, resume: StructuredResume, jd_text: str) -> List[Question]:
        """
        Planner Agent: Analyzes resume claims and JD requirements to formulate
        5 focused questions spanning technical depth, scenarios, and behavioral domains.
        """
        self.state.resume = resume
        self.state.job_description = jd_text
        self.state.candidate_name = resume.candidate_name

        # Search resume for top claims to anchor questions
        rag_claims = search_resume_claims(resume, ["rag", "fastapi", "latency", "vector", "python"])
        k8s_claims = search_resume_claims(resume, ["kubernetes", "docker", "cluster", "aws", "scale"])
        db_claims = search_resume_claims(resume, ["redis", "postgres", "database", "caching", "sql"])
        async_claims = search_resume_claims(resume, ["asyncio", "concurrency", "thread", "worker", "microservices"])

        q1_claim = rag_claims[0].text if rag_claims else "Built Python microservices and API integrations."
        q2_claim = k8s_claims[0].text if k8s_claims else "Managed containerized deployments and scaling."
        q3_claim = db_claims[0].text if db_claims else "Implemented database indexing and caching strategies."
        q4_claim = async_claims[0].text if async_claims else "Optimized asynchronous I/O and concurrency."

        questions: List[Question] = [
            Question(
                id=1,
                competency="Technical Depth",
                text=f"Your resume mentions: '{q1_claim}'. Can you explain the architectural decisions you made, how you chose the underlying libraries/frameworks, and how you measured that latency improvement in production?",
                targeted_resume_claim=q1_claim,
                jd_requirement="Production Python, microservices, and RAG/inference optimization.",
                difficulty="standard",
                evaluation_criteria="Look for specific frameworks (FastAPI/LangChain), caching/chunking strategies, and profiling metrics."
            ),
            Question(
                id=2,
                competency="Problem Solving & Scenarios",
                text=f"Suppose a high-traffic microservice running on Kubernetes suddenly experiences an exponential surge in P99 latency and intermittent 504 Gateway Timeouts. Walk me step-by-step through how you would triage, isolate, and mitigate the issue under active user load.",
                targeted_resume_claim=q2_claim,
                jd_requirement="High availability, distributed troubleshooting, and Kubernetes scaling.",
                difficulty="standard",
                evaluation_criteria="Structured troubleshooting: metric dashboards (Prometheus), pod status/OOM kills, database connection saturation, traffic shedding, or rollback."
            ),
            Question(
                id=3,
                competency="System Design & Scalability",
                text=f"In your experience designing distributed caching (such as with Redis and PostgreSQL), how do you handle cache invalidation, cache stampedes (thundering herd), and data consistency across replica nodes during high write concurrency?",
                targeted_resume_claim=q3_claim,
                jd_requirement="Scalable database patterns, Redis caching, and data consistency.",
                difficulty="standard",
                evaluation_criteria="Distributed locks (Redlock/mutex), TTL jitter, stale-while-revalidate, or write-through/write-behind semantics."
            ),
            Question(
                id=4,
                competency="Technical Depth",
                text=f"Regarding asynchronous Python: When building high-concurrency microservices, what are the subtle performance pitfalls of mixing blocking CPU-bound code inside an asyncio event loop, and how do you architect thread/process pools to avoid starving the loop?",
                targeted_resume_claim=q4_claim,
                jd_requirement="Deep understanding of asynchronous event loops, concurrency, and thread execution.",
                difficulty="standard",
                evaluation_criteria="Asyncio internals, loop.run_in_executor, ProcessPoolExecutor, GIL implications, and non-blocking I/O."
            ),
            Question(
                id=5,
                competency="Problem Solving & Scenarios",
                text="Imagine a production PostgreSQL database where write queries are deadlocking under burst traffic and connection pool limits are being exhausted. How would you analyze pg_stat_activity, configure PgBouncer pooling, and restructure transaction boundaries?",
                targeted_resume_claim="PostgreSQL optimization and connection pool management.",
                jd_requirement="Production database reliability and connection pool tuning.",
                difficulty="standard",
                evaluation_criteria="Transaction isolation levels, index locking, PgBouncer transaction pooling vs session pooling, and query plan analysis (EXPLAIN ANALYZE)."
            ),
            Question(
                id=6,
                competency="Behavioral & Ownership",
                text="Tell me about a high-stakes technical disagreement you had with a team member or product lead regarding architectural trade-offs or release timelines. How did you advocate your perspective, test assumptions, and what was the ultimate resolution?",
                targeted_resume_claim="Mentorship, cross-functional collaboration, and code reviews.",
                jd_requirement="Collaborative mindset, constructive disagreement, and technical ownership.",
                difficulty="standard",
                evaluation_criteria="STAR framework, objective data/benchmarks over ego, empathy, and business impact."
            ),
            Question(
                id=7,
                competency="Behavioral & Ownership",
                text="Walk me through a situation where a code deployment or configuration error you were responsible for caused a production degradation. How did you take ownership during the incident, communicate with stakeholders, and what systemic safeguards did you introduce post-mortem?",
                targeted_resume_claim="Production ownership and engineering rigor.",
                jd_requirement="Extreme ownership, incident command, and blameless post-mortem culture.",
                difficulty="standard",
                evaluation_criteria="Transparency, rapid mitigation over fault-finding, root-cause depth, and automated preventative controls."
            ),
            Question(
                id=8,
                competency="Communication & Clarity",
                text="How would you explain the fundamental trade-offs between asynchronous event-driven architecture (e.g., message queues) versus synchronous REST APIs to a non-technical product manager who wants real-time updates?",
                targeted_resume_claim="Clean architectural communication and team collaboration.",
                jd_requirement="Clear stakeholder communication and ability to articulate architectural trade-offs.",
                difficulty="standard",
                evaluation_criteria="Simplicity of metaphors, clarity of latency vs complexity trade-offs, and structured delivery."
            ),
            Question(
                id=9,
                competency="System Design & Scalability",
                text="When designing distributed microservices with external dependencies, how do you implement circuit breakers, retry budgets with exponential backoff, and bulkhead isolation to prevent cascading failures across the platform?",
                targeted_resume_claim="Distributed architecture and fault tolerance.",
                jd_requirement="Resilient microservice design, graceful degradation, and chaos engineering.",
                difficulty="standard",
                evaluation_criteria="Circuit breaker state machines (Open/Half-Open/Closed), jittered backoff, and rate limiting."
            ),
            Question(
                id=10,
                competency="Communication & Clarity",
                text="To wrap up: Based on your review of this role's requirements, what is one technical area where you feel your background provides immediate outsized value, and what is one domain you are most eager to ramp up on?",
                targeted_resume_claim="Job description alignment and career motivation.",
                jd_requirement="Self-awareness, growth mindset, and role alignment.",
                difficulty="standard",
                evaluation_criteria="Humility, precise alignment with JD requirements, and genuine continuous learning orientation."
            )
        ]

        self.state.questions = questions
        self.state.current_index = 0
        self.state.history = []
        self.state.status = "IN_PROGRESS"
        self.state.current_difficulty = "standard"
        self.state.active_followup = None

        record_tool_call(
            tool_name="plan_interview",
            arguments={"candidate": resume.candidate_name, "questions_count": len(questions)},
            result_summary=f"Synthesized {len(questions)} resume-anchored questions covering technical depth, scenarios, behavioral, and communication domains.",
            reasoning="Constructed comprehensive 8-10 question agenda linking candidate resume claims directly to required JD competencies."
        )

        return questions

    def get_current_question(self) -> Optional[Question]:
        """Returns the current active base question."""
        if 0 <= self.state.current_index < len(self.state.questions):
            return self.state.questions[self.state.current_index]
        return None

    def submit_answer(self, answer_text: str) -> Dict[str, Any]:
        """
        Agentic Execution Loop:
        1. Evaluates candidate response using evaluate_answer tool
        2. Validates score evidence using validate_score_evidence tool
        3. Decides whether to trigger a targeted follow-up probe (if answer is shallow)
        4. Or advances to next competency and adjusts difficulty
        """
        curr_q = self.get_current_question()
        if not curr_q:
            return {"status": "error", "message": "No active question."}

        # Step 1: If awaiting follow-up response
        if self.state.status == "AWAITING_FOLLOWUP":
            return self._handle_followup_answer(answer_text, curr_q)

        # Step 2: Evaluating initial answer
        evaluation = evaluate_answer(
            question_text=curr_q.text,
            candidate_answer=answer_text,
            competency=curr_q.competency,
            resume_claims=self.state.resume.claims if self.state.resume else []
        )

        # Step 3: Validate evidence
        validation = validate_score_evidence(
            candidate_answer=answer_text,
            score=evaluation.score,
            explanation=evaluation.rubric_match
        )

        # Step 4: Agent decision - follow-up required?
        if evaluation.needs_followup and evaluation.suggested_followup_prompt:
            self.state.status = "AWAITING_FOLLOWUP"
            self.state.active_followup = evaluation.suggested_followup_prompt

            # Store partial turn record
            temp_turn = TurnRecord(
                question_id=curr_q.id,
                competency=curr_q.competency,
                question=curr_q.text,
                targeted_resume_claim=curr_q.targeted_resume_claim,
                answer=answer_text,
                evaluation=evaluation,
                followup_question=evaluation.suggested_followup_prompt,
                final_score=evaluation.score,
                difficulty=self.state.current_difficulty
            )
            self.state.history.append(temp_turn)

            record_tool_call(
                tool_name="adaptive_agent_decision",
                arguments={"decision": "trigger_followup", "completeness": evaluation.completeness},
                result_summary=f"Selected follow-up because response was shallow (Completeness: {round(evaluation.completeness*100)}%).",
                reasoning=f"Candidate answer lacked depth in {curr_q.competency}. Probing with targeted follow-up before scoring."
            )

            return {
                "status": "followup_required",
                "followup_question": self.state.active_followup,
                "evaluation": evaluation,
                "reason": "The initial answer lacked technical specifics or trade-off evaluation. Probing for depth."
            }

        # Step 5: Answer is sufficient -> advance question
        turn = TurnRecord(
            question_id=curr_q.id,
            competency=curr_q.competency,
            question=curr_q.text,
            targeted_resume_claim=curr_q.targeted_resume_claim,
            answer=answer_text,
            evaluation=evaluation,
            final_score=evaluation.score,
            difficulty=self.state.current_difficulty
        )
        self.state.history.append(turn)

        # Adaptive difficulty adjustment
        if evaluation.score >= 4 and self.state.current_difficulty != "advanced":
            self.state.current_difficulty = "advanced"
        elif evaluation.score <= 2 and self.state.current_difficulty != "foundational":
            self.state.current_difficulty = "foundational"

        # Check coverage
        coverage = check_competency_coverage(
            [t.model_dump() for t in self.state.history],
            TARGET_COMPETENCIES
        )

        self.state.current_index += 1

        # Check if interview complete
        if self.state.current_index >= len(self.state.questions):
            self._finalize_interview()
            return {
                "status": "completed",
                "turn": turn,
                "coverage": coverage
            }

        record_tool_call(
            tool_name="adaptive_agent_decision",
            arguments={"decision": "advance_question", "score": evaluation.score, "next_difficulty": self.state.current_difficulty},
            result_summary=f"Advanced to Question #{self.state.current_index + 1}. Current Difficulty: {self.state.current_difficulty.upper()}",
            reasoning=f"Sufficient evidence recorded for {curr_q.competency}. Stepping forward in interview plan."
        )

        return {
            "status": "advanced",
            "turn": turn,
            "next_question": self.get_current_question(),
            "coverage": coverage
        }

    def _handle_followup_answer(self, followup_answer_text: str, curr_q: Question) -> Dict[str, Any]:
        """Processes the candidate's answer to an adaptive follow-up probe."""
        # Find active turn in history
        turn = self.state.history[-1]
        turn.followup_answer = followup_answer_text

        # Evaluate the follow-up
        followup_eval = evaluate_answer(
            question_text=self.state.active_followup or "",
            candidate_answer=followup_answer_text,
            competency=curr_q.competency,
            resume_claims=self.state.resume.claims if self.state.resume else []
        )
        turn.followup_evaluation = followup_eval

        # Combine scores: reward recovery if candidate gave strong follow-up
        if followup_eval.score > turn.evaluation.score:
            improved_score = min(5, turn.evaluation.score + (followup_eval.score - turn.evaluation.score))
            turn.final_score = improved_score
        else:
            turn.final_score = turn.evaluation.score

        # Reset follow-up state
        self.state.status = "IN_PROGRESS"
        self.state.active_followup = None

        # Check coverage
        coverage = check_competency_coverage(
            [t.model_dump() for t in self.state.history],
            TARGET_COMPETENCIES
        )

        self.state.current_index += 1

        record_tool_call(
            tool_name="adaptive_agent_decision",
            arguments={"decision": "followup_completed", "initial_score": turn.evaluation.score, "adjusted_score": turn.final_score},
            result_summary=f"Follow-up probe resolved. Final competency score: {turn.final_score}/5.",
            reasoning="Combined initial and follow-up responses to establish definitive competency rating."
        )

        if self.state.current_index >= len(self.state.questions):
            self._finalize_interview()
            return {
                "status": "completed",
                "turn": turn,
                "coverage": coverage
            }

        return {
            "status": "advanced",
            "turn": turn,
            "next_question": self.get_current_question(),
            "coverage": coverage
        }

    def _finalize_interview(self) -> None:
        """Runs end-of-interview tools: consistency checking and status finalization."""
        self.state.status = "COMPLETED"

        # Tool: detect_consistency
        resume_claims = self.state.resume.claims if self.state.resume else []
        history_dicts = [t.model_dump() for t in self.state.history]
        findings = detect_consistency(resume_claims, history_dicts)
        self.state.consistency_findings = findings

        record_tool_call(
            tool_name="finalize_interview_report",
            arguments={"total_turns": len(self.state.history), "verified_claims": len(findings)},
            result_summary="Completed first-round screening session. Generated consistency matrix and final scorecard.",
            reasoning="All 5 core competencies probed. Compiled objective audit log for human recruiter evaluation."
        )

    def reset_interview(self) -> None:
        """Reset state for a new interview session."""
        from tools import clear_activity_logs
        clear_activity_logs()
        self.state = InterviewState()
