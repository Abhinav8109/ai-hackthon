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

    def plan_interview(self, resume: StructuredResume, jd_text: str, job_title: str = "") -> List[Question]:
        """
        Planner Agent: Analyzes candidate resume claims and target job requirements to formulate
        8-10 high-caliber questions dynamically tailored across the 5 enterprise disciplines:
        - Lead DevOps & SRE
        - Senior AI Systems Engineer
        - Senior Frontend Architect
        - Senior Data Platform Engineer
        - Senior Backend / Software Engineer
        """
        self.state.resume = resume
        self.state.job_description = jd_text
        self.state.candidate_name = resume.candidate_name
        self.state.job_title = job_title or "Senior Software Engineer"

        role_context = (job_title + " " + jd_text).lower()

        # Extract anchor claims based on role
        if "devops" in role_context or "sre" in role_context or "cloud" in role_context:
            primary_claims = search_resume_claims(resume, ["kubernetes", "terraform", "aws", "prometheus", "ci/cd", "helm"])
            claim_text = primary_claims[0].text if primary_claims else "Orchestrated cloud infrastructure and CI/CD pipelines."
            questions = [
                Question(
                    id=1,
                    competency="Technical Depth",
                    text=f"Your resume highlights: '{claim_text}'. How did you structure your infrastructure-as-code and container orchestration? Specifically, how do you handle state locking in Terraform, zero-downtime rolling updates, and cluster-wide resource quotas?",
                    targeted_resume_claim=claim_text,
                    jd_requirement="Production Kubernetes, Terraform state management, and cloud infrastructure.",
                    difficulty="standard",
                    evaluation_criteria="Terraform state locks (DynamoDB/S3), PodDisruptionBudgets, resource requests/limits, and HPA."
                ),
                Question(
                    id=2,
                    competency="Problem Solving & Scenarios",
                    text="During peak production traffic, several critical pods enter a CrashLoopBackOff state due to memory limits (OOMKilled), and your ingress controller starts throwing 504 Gateway Timeouts. Walk me step-by-step through how you isolate the root cause, mitigate the outage, and prevent recurrence.",
                    targeted_resume_claim="Kubernetes cluster troubleshooting and incident mitigation.",
                    jd_requirement="Incident response, container debugging, and metric observability.",
                    difficulty="standard",
                    evaluation_criteria="kubectl describe/logs, cgroup OOM verification, temporary limit adjustments, traffic throttling, and node autoscaling."
                ),
                Question(
                    id=3,
                    competency="System Design & Scalability",
                    text="How would you design a multi-region, active-active AWS EKS deployment that achieves 99.99% availability, minimizes cross-region latency, and handles automated disaster recovery failover?",
                    targeted_resume_claim="Multi-region cloud architecture and high availability.",
                    jd_requirement="High availability, distributed DNS/Route53, and multi-region resilience.",
                    difficulty="standard",
                    evaluation_criteria="Route 53 latency routing, health checks, Cross-Region VPC peering, stateless worker pools, and database replication lag."
                ),
                Question(
                    id=4,
                    competency="Technical Depth",
                    text="In production monitoring, how do you eliminate alert fatigue while defining meaningful SLIs, SLOs, and error budget burn rates with Prometheus and Grafana for critical services?",
                    targeted_resume_claim="Observability and alerting frameworks.",
                    jd_requirement="SRE metrics, Prometheus query language (PromQL), and alert budgeting.",
                    difficulty="standard",
                    evaluation_criteria="Multi-window multi-burn-rate alerts, latency percentile SLIs, and symptom-based over cause-based alerting."
                ),
                Question(
                    id=5,
                    competency="Problem Solving & Scenarios",
                    text="Suppose a newly deployed Helm release causes silent connection leaks to downstream services. How do you automate canary analysis and automated rollback using tools like Flagger, Argo Rollouts, or custom Prometheus metrics?",
                    targeted_resume_claim="Automated canary deployments and CI/CD pipelines.",
                    jd_requirement="Continuous delivery, progressive deployment, and automated canary analysis.",
                    difficulty="standard",
                    evaluation_criteria="Canary traffic stepping (5% -> 20% -> 50%), metric thresholds (HTTP 5xx rate and P99 latency), and automated rollback triggers."
                ),
                Question(
                    id=6,
                    competency="Behavioral & Ownership",
                    text="Describe a high-severity production incident where an infrastructure change you were responsible for caused downtime. How did you coordinate with on-call responders, manage stakeholder expectations, and conduct a blameless post-mortem?",
                    targeted_resume_claim="Production ownership and blameless post-mortem culture.",
                    jd_requirement="Extreme ownership, incident command, and preventative engineering.",
                    difficulty="standard",
                    evaluation_criteria="Transparency, focus on systemic prevention over individual blame, and automated guardrails."
                ),
                Question(
                    id=7,
                    competency="System Design & Scalability",
                    text="When securing Kubernetes clusters, how do you implement zero-trust network policies, mutual TLS (mTLS) with service meshes (e.g., Istio/Linkerd), and automated secret rotation without disrupting live traffic?",
                    targeted_resume_claim="Cluster security and network policies.",
                    jd_requirement="Container security, service mesh, and secret lifecycle management.",
                    difficulty="standard",
                    evaluation_criteria="NetworkPolicies (default-deny), Istio PeerAuthentication, Vault integration, and ExternalSecrets operator."
                ),
                Question(
                    id=8,
                    competency="Communication & Clarity",
                    text="How would you explain the trade-offs between hosting our own self-managed Kubernetes control plane versus paying for a fully managed service (like AWS EKS or GCP GKE) to a Chief Financial Officer?",
                    targeted_resume_claim="Technical communication and cost governance.",
                    jd_requirement="Cost-benefit articulation, operational overhead, and financial trade-offs.",
                    difficulty="standard",
                    evaluation_criteria="Total Cost of Ownership (TCO), engineering hours vs cloud provider SLAs, and maintenance risk."
                ),
                Question(
                    id=9,
                    competency="Problem Solving & Scenarios",
                    text="When configuring Linux kernel parameters and container runtime settings (such as somaxconn, file descriptor limits, and ephemeral port exhaustion) for high-throughput network services, what failure modes do you look for?",
                    targeted_resume_claim="Linux kernel tuning and systems performance.",
                    jd_requirement="Systems-level debugging and OS performance tuning.",
                    difficulty="standard",
                    evaluation_criteria="sysctl tuning (net.core.somaxconn, ip_local_port_range), ulimit settings, and TIME_WAIT socket reuse."
                ),
                Question(
                    id=10,
                    competency="Communication & Clarity",
                    text="Based on your experience, what is one modern cloud or SRE practice that you believe is currently over-hyped, and what is one foundational practice that engineering teams consistently neglect?",
                    targeted_resume_claim="Engineering philosophy and continuous improvement.",
                    jd_requirement="Pragmatism, engineering judgment, and technical self-awareness.",
                    difficulty="standard",
                    evaluation_criteria="Nuanced critical thinking, empirical justification, and practical balance."
                )
            ]

        elif "ai" in role_context or "machine learning" in role_context or "rag" in role_context:
            primary_claims = search_resume_claims(resume, ["rag", "vector", "chromadb", "langchain", "pytorch", "llm"])
            claim_text = primary_claims[0].text if primary_claims else "Engineered enterprise RAG and LLM inference pipelines."
            questions = [
                Question(
                    id=1,
                    competency="Technical Depth",
                    text=f"Your resume highlights: '{claim_text}'. Walk me through your RAG architecture: How did you select your chunking strategy, choose embedding models, and benchmark vector search retrieval latency versus recall accuracy?",
                    targeted_resume_claim=claim_text,
                    jd_requirement="Production RAG architecture, vector search, and embedding models.",
                    difficulty="standard",
                    evaluation_criteria="Chunking overlap, semantic chunking, embedding dimensionalities, and HNSW index tuning."
                ),
                Question(
                    id=2,
                    competency="Problem Solving & Scenarios",
                    text="A production LLM application begins producing severe hallucinations on legal/financial documents after a chunk size update, and P99 latency spikes above 3 seconds. How do you systematically diagnose whether the breakdown is in retrieval relevance, context window truncation, or model prompt drift?",
                    targeted_resume_claim="LLM evaluation and hallucination debugging.",
                    jd_requirement="RAG evaluation, automated metrics, and latency optimization.",
                    difficulty="standard",
                    evaluation_criteria="RAGAS metrics (Faithfulness, Answer Relevance), top-k retrieval auditing, rerankers (Cohere/Cross-Encoder), and prompt token budgets."
                ),
                Question(
                    id=3,
                    competency="System Design & Scalability",
                    text="How would you architect a distributed semantic caching layer for millions of high-throughput LLM queries that balances cosine similarity thresholding with cache invalidation when underlying knowledge bases update?",
                    targeted_resume_claim="Semantic caching and vector database scalability.",
                    jd_requirement="Vector caching, cache invalidation, and low-latency inference.",
                    difficulty="standard",
                    evaluation_criteria="Vector index caching (Redis/GPTCache), similarity threshold tuning (e.g. 0.92), and asynchronous document update invalidation."
                ),
                Question(
                    id=4,
                    competency="Technical Depth",
                    text="What are the concrete technical trade-offs between parameter-efficient fine-tuning (LoRA / QLoRA) on open-source weights versus in-context few-shot learning on a hosted frontier model for domain-specific tasks?",
                    targeted_resume_claim="Model fine-tuning and adaptation.",
                    jd_requirement="Fine-tuning methodologies, rank adaptation, and cost/latency trade-offs.",
                    difficulty="standard",
                    evaluation_criteria="Rank matrix adjustments, memory footprint (4-bit quantization), training cost, and catastrophic forgetting risks."
                ),
                Question(
                    id=5,
                    competency="Problem Solving & Scenarios",
                    text="During batched GPU inference under peak customer traffic, your inference cluster experiences GPU out-of-memory (OOM) errors and request timeouts. How do you implement dynamic batching, KV-cache management (e.g., PagedAttention / vLLM), and request queuing?",
                    targeted_resume_claim="GPU inference optimization and throughput scaling.",
                    jd_requirement="Serving optimization, vLLM / TensorRT-LLM, and memory management.",
                    difficulty="standard",
                    evaluation_criteria="PagedAttention, continuous batching, KV-cache fragmentation mitigation, and max token limits."
                ),
                Question(
                    id=6,
                    competency="Behavioral & Ownership",
                    text="Tell me about a time when an AI feature you developed failed to meet accuracy benchmarks or generated unexpected edge-case outputs right before a scheduled release. How did you communicate this to leadership and resolve the issue?",
                    targeted_resume_claim="Cross-functional delivery and engineering ownership.",
                    jd_requirement="Technical integrity, stakeholder transparency, and risk mitigation.",
                    difficulty="standard",
                    evaluation_criteria="Transparency with stakeholders, fallback heuristics, and automated regression evaluations."
                ),
                Question(
                    id=7,
                    competency="System Design & Scalability",
                    text="How do you architect defensive guardrails against prompt injection, jailbreaks, and sensitive data leakage (PII) before queries reach your inference models?",
                    targeted_resume_claim="AI safety, alignment, and data security.",
                    jd_requirement="LLM security, input sanitization, and output validation.",
                    difficulty="standard",
                    evaluation_criteria="Input sanitization classifiers, secondary evaluator models, NeMo Guardrails, and regex/NER masking."
                ),
                Question(
                    id=8,
                    competency="Communication & Clarity",
                    text="How would you explain the difference between vector similarity search (cosine distance in high-dimensional space) versus traditional keyword search (BM25/Elasticsearch) to a non-technical product manager?",
                    targeted_resume_claim="Technical communication and architectural clarity.",
                    jd_requirement="Conceptual translation, intuitive metaphors, and trade-off explanation.",
                    difficulty="standard",
                    evaluation_criteria="Semantic meaning vs exact keyword matching, hybrid search advantages, and intuitive analogies."
                ),
                Question(
                    id=9,
                    competency="Problem Solving & Scenarios",
                    text="When evaluating open-source foundation models for edge deployment, how do you evaluate model quantization (INT8 vs INT4) trade-offs between perplexity degradation, memory bandwidth, and inference speed?",
                    targeted_resume_claim="Model quantization and edge optimization.",
                    jd_requirement="Quantization techniques (AWQ, GPTQ, GGUF), and hardware constraints.",
                    difficulty="standard",
                    evaluation_criteria="Perplexity benchmarks, memory bandwidth bottlenecks, and target hardware constraints."
                ),
                Question(
                    id=10,
                    competency="Communication & Clarity",
                    text="Looking forward, what do you see as the most critical bottleneck currently limiting enterprise adoption of autonomous agentic workflows?",
                    targeted_resume_claim="Industry vision and continuous learning.",
                    jd_requirement="Agentic architecture awareness, tool validation, and deterministic reliability.",
                    difficulty="standard",
                    evaluation_criteria="Tool validation accuracy, loop termination guarantees, state persistence, and human-in-the-loop oversight."
                )
            ]

        elif "frontend" in role_context or "react" in role_context or "next" in role_context:
            primary_claims = search_resume_claims(resume, ["react", "next.js", "typescript", "redux", "web vitals"])
            claim_text = primary_claims[0].text if primary_claims else "Built enterprise frontend architectures with Next.js and TypeScript."
            questions = [
                Question(
                    id=1,
                    competency="Technical Depth",
                    text=f"Your resume mentions: '{claim_text}'. How do you architect server-side rendering (SSR) and static site generation (SSG) in Next.js to optimize Core Web Vitals (specifically LCP, CLS, and INP)?",
                    targeted_resume_claim=claim_text,
                    jd_requirement="Next.js architecture, Core Web Vitals, and rendering pipelines.",
                    difficulty="standard",
                    evaluation_criteria="Streaming SSR, font optimization, dynamic imports, and cumulative layout shift elimination."
                ),
                Question(
                    id=2,
                    competency="Problem Solving & Scenarios",
                    text="A mission-critical dashboard with heavy real-time data streaming begins experiencing severe Interaction to Next Paint (INP) delays and main-thread freezes. How do you profile the Chrome performance timeline, locate expensive re-renders, and offload CPU work?",
                    targeted_resume_claim="Frontend performance optimization and profiling.",
                    jd_requirement="Chrome DevTools Profiler, React reconciliation, and main-thread scheduling.",
                    difficulty="standard",
                    evaluation_criteria="Chrome Performance panel, React DevTools Profiler, Web Workers for heavy computations, and useDeferredValue / useTransition."
                ),
                Question(
                    id=3,
                    competency="System Design & Scalability",
                    text="How do you architect a shared design system component library across multiple independent product applications to ensure consistent branding, zero bundle bloat, and strict semantic versioning?",
                    targeted_resume_claim="Design systems and modular frontend architecture.",
                    jd_requirement="Modular components, tree-shaking, and multi-app governance.",
                    difficulty="standard",
                    evaluation_criteria="Tree-shaking (ESM exports), Tailwind/CSS variables, headless components (Radix/Aria), and automated visual regression testing."
                ),
                Question(
                    id=4,
                    competency="Technical Depth",
                    text="When choosing between centralized state management (Redux/Zustand) versus server state libraries (TanStack React Query / SWR), how do you draw boundaries to prevent cache duplication and memory leaks?",
                    targeted_resume_claim="State management architecture and data synchronization.",
                    jd_requirement="Client state vs server cache, optimistic UI updates, and cache invalidation.",
                    difficulty="standard",
                    evaluation_criteria="Separation of client UI state vs server cache, stale time management, and garbage collection."
                ),
                Question(
                    id=5,
                    competency="Problem Solving & Scenarios",
                    text="Users on low-powered mobile devices report that client-side hydration fails with subtle mismatch errors and double-renders. How do you diagnose hydration mismatches in React Server Components and implement progressive hydration?",
                    targeted_resume_claim="React hydration and responsive performance.",
                    jd_requirement="Server-Client hydration, React 18/19 server components, and progressive loading.",
                    difficulty="standard",
                    evaluation_criteria="Identifying non-deterministic browser APIs (Date, window) in SSR, Suspense boundaries, and selective hydration."
                ),
                Question(
                    id=6,
                    competency="Behavioral & Ownership",
                    text="Tell me about a time when you had to advocate for technical debt cleanup or performance refactoring against strong pushback from product managers who wanted new features immediately. How did you build alignment?",
                    targeted_resume_claim="Technical leadership and stakeholder advocacy.",
                    jd_requirement="Cross-functional influence, business alignment, and engineering rigor.",
                    difficulty="standard",
                    evaluation_criteria="Linking Web Vitals and load speed directly to user conversion and bounce rates."
                ),
                Question(
                    id=7,
                    competency="Technical Depth",
                    text="How do you enforce WCAG 2.1 AA accessibility standards across interactive complex components like multi-select dropdowns, modal focus traps, and screen-reader live regions?",
                    targeted_resume_claim="Web accessibility and inclusive design.",
                    jd_requirement="WCAG guidelines, ARIA attributes, keyboard navigation, and focus management.",
                    difficulty="standard",
                    evaluation_criteria="ARIA roles, keyboard event listeners (Escape, Tab traps), and aria-live announcements."
                ),
                Question(
                    id=8,
                    competency="Communication & Clarity",
                    text="How would you explain the architectural concept of React Server Components and streaming HTML to a junior engineer who is only familiar with client-side SPAs?",
                    targeted_resume_claim="Engineering mentorship and conceptual clarity.",
                    jd_requirement="Technical mentoring, visual explanation, and mental model building.",
                    difficulty="standard",
                    evaluation_criteria="Zero client bundle impact, direct server access, and streaming chunk boundaries."
                ),
                Question(
                    id=9,
                    competency="System Design & Scalability",
                    text="How do you architect a micro-frontend setup (or modular monorepo) allowing 5 independent engineering teams to deploy frontend features autonomously without breaking shared routing or dependencies?",
                    targeted_resume_claim="Micro-frontend architectures and monorepos.",
                    jd_requirement="Module Federation, Turborepo, and distributed frontend builds.",
                    difficulty="standard",
                    evaluation_criteria="Webpack Module Federation, shared runtime dependencies, isolated versioning, and shared shell apps."
                ),
                Question(
                    id=10,
                    competency="Communication & Clarity",
                    text="What is your philosophy on automated testing for frontends: where do you draw the line between unit tests, integration tests with testing-library, and end-to-end tests with Playwright?",
                    targeted_resume_claim="Testing strategy and code quality.",
                    jd_requirement="Testing pyramid, user-centric testing, and CI execution speed.",
                    difficulty="standard",
                    evaluation_criteria="Testing user behavior rather than implementation details, mock service workers (MSW), and E2E critical paths."
                )
            ]

        elif "data" in role_context or "kafka" in role_context or "spark" in role_context:
            primary_claims = search_resume_claims(resume, ["kafka", "spark", "snowflake", "airflow", "sql"])
            claim_text = primary_claims[0].text if primary_claims else "Engineered large-scale distributed data pipelines with Kafka and Spark."
            questions = [
                Question(
                    id=1,
                    competency="Technical Depth",
                    text=f"Your resume highlights: '{claim_text}'. Walk me through your streaming architecture: How do you configure Kafka partition counts, consumer group rebalancing, and consumer offset commit strategies to guarantee exactly-once processing semantics?",
                    targeted_resume_claim=claim_text,
                    jd_requirement="Kafka architecture, partition tuning, and exactly-once processing.",
                    difficulty="standard",
                    evaluation_criteria="Transactional producers, read_committed consumers, idempotent producers, and partition key strategy."
                ),
                Question(
                    id=2,
                    competency="Problem Solving & Scenarios",
                    text="A distributed Apache Spark ETL batch job that processes 10TB of event data daily suddenly fails with Executor OutOfMemory errors and severe shuffle spill to disk. How do you diagnose data skew, adjust partition boundaries, and optimize broadcast joins?",
                    targeted_resume_claim="Spark optimization and memory debugging.",
                    jd_requirement="Spark internals, memory allocation, shuffle tuning, and data skew mitigation.",
                    difficulty="standard",
                    evaluation_criteria="Spark UI analysis (shuffle read/write, task skew), salting keys to redistribute partitions, and broadcast join thresholds."
                ),
                Question(
                    id=3,
                    competency="System Design & Scalability",
                    text="How would you design a petabyte-scale Lakehouse architecture on Snowflake/Delta Lake that supports both sub-second interactive BI analytics and high-throughput real-time streaming ingestion?",
                    targeted_resume_claim="Lakehouse design and data warehouse modeling.",
                    jd_requirement="Medallion architecture (Bronze/Silver/Gold), clustering keys, and micro-batching.",
                    difficulty="standard",
                    evaluation_criteria="Bronze/Silver/Gold layers, Snowflake auto-clustering, Snowpipe streaming, and query pruning."
                ),
                Question(
                    id=4,
                    competency="Technical Depth",
                    text="When orchestrating mission-critical DAGs in Apache Airflow, how do you enforce idempotency, manage backfills, and configure dynamic sensor timeouts to prevent worker pool starvation?",
                    targeted_resume_claim="Airflow orchestration and workflow automation.",
                    jd_requirement="Idempotent pipeline design, DAG scheduling, and worker resource pools.",
                    difficulty="standard",
                    evaluation_criteria="Partition-based staging tables, reschedule mode on sensors, and deterministic rerun logic."
                ),
                Question(
                    id=5,
                    competency="Problem Solving & Scenarios",
                    text="Downstream analytics models report subtle data corruption caused by upstream microservices introducing unannounced schema alterations. How do you implement automated schema registry validation, dead letter queues (DLQ), and data contracts (e.g., Great Expectations / dbt tests)?",
                    targeted_resume_claim="Data quality and schema governance.",
                    jd_requirement="Schema evolution, Confluent Schema Registry, and automated quality testing.",
                    difficulty="standard",
                    evaluation_criteria="Schema compatibility modes (FULL/BACKWARD), schema registry enforcement, DLQs, and pre-commit dbt tests."
                ),
                Question(
                    id=6,
                    competency="Behavioral & Ownership",
                    text="Describe a scenario where a critical data pipeline failure resulted in stale metrics being delivered to executive leadership or external financial audits. How did you handle the situation and establish systemic safeguards?",
                    targeted_resume_claim="Data reliability and production responsibility.",
                    jd_requirement="Accountability, data lineage, and automated anomaly alerting.",
                    difficulty="standard",
                    evaluation_criteria="Immediate stakeholder notification, automated circuit breaking on corrupted feeds, and SLA alerting."
                ),
                Question(
                    id=7,
                    competency="System Design & Scalability",
                    text="How do you handle late-arriving events and watermarking in real-time stream processing engines (e.g., Apache Flink or Spark Structured Streaming) without blowing up state storage?",
                    targeted_resume_claim="Stream processing and windowing.",
                    jd_requirement="Watermarking, event-time processing, and stateful stream management.",
                    difficulty="standard",
                    evaluation_criteria="Allowed lateness policies, event-time watermarks, and RocksDB state backend pruning."
                ),
                Question(
                    id=8,
                    competency="Communication & Clarity",
                    text="How would you articulate the return on investment (ROI) of migrating from a traditional legacy relational data warehouse to a modern cloud data lakehouse to non-technical business stakeholders?",
                    targeted_resume_claim="Business communication and data strategy.",
                    jd_requirement="Cost governance, query speed, and self-serve business intelligence.",
                    difficulty="standard",
                    evaluation_criteria="Decoupling compute from storage, elastic scaling, and enabling advanced analytics and AI workloads."
                ),
                Question(
                    id=9,
                    competency="Technical Depth",
                    text="When modeling dimensional schemas (Kimball methodology) versus wide denormalized tables in modern columnar engines, how do you evaluate compression efficiency and scan costs?",
                    targeted_resume_claim="Data modeling and storage efficiency.",
                    jd_requirement="Columnar storage (Parquet/ORC), projection efficiency, and join performance.",
                    difficulty="standard",
                    evaluation_criteria="Parquet dictionary encoding, run-length compression, and minimizing full-table scan bytes."
                ),
                Question(
                    id=10,
                    competency="Communication & Clarity",
                    text="What is your criteria for deciding when a data engineering pipeline should be strictly real-time streaming versus when simple 15-minute micro-batches are more pragmatic?",
                    targeted_resume_claim="Engineering pragmatism and architectural trade-offs.",
                    jd_requirement="Complexity cost vs real-time necessity, operational overhead, and reliability.",
                    difficulty="standard",
                    evaluation_criteria="Business SLA requirements, operational overhead of stateful streaming, and cost trade-offs."
                )
            ]

        else:
            # Default: Senior Backend Software Engineer (Python & Distributed Systems)
            primary_claims = search_resume_claims(resume, ["fastapi", "redis", "postgres", "microservices", "asyncio", "python"])
            claim_text = primary_claims[0].text if primary_claims else "Engineered scalable Python microservices and distributed database layers."
            questions = [
                Question(
                    id=1,
                    competency="Technical Depth",
                    text=f"Your resume mentions: '{claim_text}'. Can you explain the architectural decisions you made, how you chose the underlying libraries/frameworks, and how you measured that latency improvement in production?",
                    targeted_resume_claim=claim_text,
                    jd_requirement="Production Python, microservices, and high-throughput APIs.",
                    difficulty="standard",
                    evaluation_criteria="Look for specific frameworks (FastAPI/SQLAlchemy), caching strategies, and profiling metrics."
                ),
                Question(
                    id=2,
                    competency="Problem Solving & Scenarios",
                    text="Suppose a high-traffic microservice running on Kubernetes suddenly experiences an exponential surge in P99 latency and intermittent 504 Gateway Timeouts under burst load. Walk me step-by-step through how you would triage, isolate, and mitigate the issue under active user load.",
                    targeted_resume_claim="Distributed troubleshooting and production incident response.",
                    jd_requirement="High availability, distributed troubleshooting, and latency mitigation.",
                    difficulty="standard",
                    evaluation_criteria="Structured troubleshooting: metric dashboards (Prometheus), pod status/OOM kills, database connection saturation, and rollback."
                ),
                Question(
                    id=3,
                    competency="System Design & Scalability",
                    text="In your experience designing distributed caching (such as with Redis and PostgreSQL), how do you handle cache invalidation, cache stampedes (thundering herd), and data consistency across replica nodes during high write concurrency?",
                    targeted_resume_claim="Distributed caching and database optimization.",
                    jd_requirement="Scalable database patterns, Redis caching, and data consistency.",
                    difficulty="standard",
                    evaluation_criteria="Distributed locks (Redlock/mutex), TTL jitter, stale-while-revalidate, or write-through semantics."
                ),
                Question(
                    id=4,
                    competency="Technical Depth",
                    text="Regarding asynchronous Python: When building high-concurrency microservices, what are the subtle performance pitfalls of mixing blocking CPU-bound code inside an asyncio event loop, and how do you architect thread/process pools to avoid starving the loop?",
                    targeted_resume_claim="Asynchronous programming and event loop performance.",
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
            arguments={"candidate": resume.candidate_name, "role": self.state.job_title, "questions_count": len(questions)},
            result_summary=f"Synthesized {len(questions)} resume-anchored questions tailored for {self.state.job_title}.",
            reasoning=f"Constructed role-specialized 10-question agenda covering technical depth, scenarios, behavioral, and communication domains for {self.state.job_title}."
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
