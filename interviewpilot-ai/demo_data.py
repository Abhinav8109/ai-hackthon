"""
Synthetic Demo Data Module for InterviewPilot AI.
Provides a realistic, clearly-labeled synthetic Python developer resume and
Job Description for 1-click zero-dependency hackathon demonstrations.
Also includes pre-crafted shallow and strong answers for easy live testing.
"""

SYNTHETIC_RESUME_TEXT = """
Alex Chen
Email: alex.chen.dev@example.com | Phone: (555) 432-8765 | GitHub: github.com/alexchen-dev
Location: San Francisco, CA | LinkedIn: linkedin.com/in/alexchen-demo

PROFESSIONAL SUMMARY
Results-driven Senior Python & AI Platform Engineer with 5+ years of experience designing high-throughput distributed microservices, building LLM RAG pipelines, and deploying containerized cloud systems on AWS and Kubernetes.

CORE TECHNICAL SKILLS
• Languages: Python (Expert), SQL, TypeScript, Go (Intermediate)
• Frameworks: FastAPI, Django, Flask, PyTorch, LangChain, Pydantic, SQLAlchemy
• Databases & Caching: PostgreSQL, Redis (Cluster, Pub/Sub), ChromaDB, Pinecone
• Cloud & DevOps: AWS (ECS, Lambda, S3, RDS), Docker, Kubernetes, CI/CD GitHub Actions, Prometheus
• Architecture: Distributed Systems, Microservices, REST APIs, Asynchronous Programming (asyncio), Caching Strategies

PROFESSIONAL EXPERIENCE

Senior Backend & AI Engineer | CloudScale AI Solutions (2022 - Present)
• Architected and deployed an enterprise Retrieval-Augmented Generation (RAG) pipeline using FastAPI, LangChain, and ChromaDB, reducing end-to-end query latency by 42% (from 1.8s down to 240ms).
• Spearheaded Kubernetes container migration on AWS EKS, orchestrating auto-scaling clusters that reliably handled 25,000 requests/sec with 99.99% uptime.
• Designed a distributed Redis caching layer with stale-while-revalidate invalidation, eliminating redundant database calls and saving $14,000/month in cloud infrastructure costs.
• Mentored 4 junior engineers on asynchronous Python patterns, clean architecture, and automated test-driven development.

Software Engineer | FinFlow Systems (2019 - 2022)
• Developed high-volume payment processing microservices using Python, Django REST Framework, and PostgreSQL handling $3M+ in daily transaction volume.
• Resolved critical database lock contention issues in PostgreSQL by introducing read replicas and connection pooling with pgBouncer.
• Implemented automated CI/CD pipelines with GitHub Actions and Docker, reducing deployment cycle times from 45 minutes to under 6 minutes.

EDUCATION & CERTIFICATIONS
• B.S. in Computer Science | University of California, Berkeley (2019)
• AWS Certified Solutions Architect - Associate (2023)
"""

SYNTHETIC_JD_TEXT = """
Role: Senior AI Systems & Backend Engineer (Python / Distributed Systems)
Company: NexusAI Enterprise Technologies
Location: Remote / Hybrid

About the Role:
We are seeking an experienced Senior AI Systems Engineer to spearhead our next-generation enterprise AI platform. You will design resilient, low-latency microservices that serve LLM workflows, optimize distributed data pipelines, and maintain scalable cloud architecture.

Key Responsibilities:
• Architect, build, and maintain production-grade REST APIs and microservices using Python (FastAPI/asyncio) and PostgreSQL.
• Design and optimize AI inference and RAG pipelines utilizing vector databases (ChromaDB/Pinecone) and LLM frameworks.
• Scale distributed systems across Kubernetes clusters and AWS infrastructure with observability and automated failover.
• Collaborate with cross-functional product, AI research, and frontend teams to deliver business-critical features.
• Champion engineering best practices, code reviews, and architectural trade-off evaluations.

Requirements & Qualifications:
• 4+ years of professional backend development experience with strong proficiency in Python and asynchronous programming.
• Hands-on production experience with Docker, Kubernetes, and AWS cloud environments.
• Experience building or optimizing RAG pipelines, vector search, or embeddings.
• Deep understanding of database performance tuning (PostgreSQL, Redis caching, query optimization).
• Excellent communication skills, structured problem-solving approach, and ability to mentor team members.
"""

# Pre-crafted sample responses for live testing in hackathons
SAMPLE_RESPONSES = {
    "shallow": {
        "text": "I used Redis to cache things. It made the system faster and reduced database load. We had a Docker setup for deployment.",
        "label": "⚠️ Test Shallow Answer (Triggers Follow-up Probe)"
    },
    "strong": {
        "text": "In our FastAPI service, we implemented a dual-layer caching strategy. We used an in-memory LRU cache for hot static metadata and a Redis cluster with TTLs for user-specific session states. To prevent cache stampedes during traffic spikes, we used distributed mutex locks and a stale-while-revalidate pattern. This dropped P99 latency from 450ms down to 35ms and reduced database CPU utilization by 65%.",
        "label": "✅ Test Strong Answer (Advances with High Score)"
    },
    "scenario_shallow": {
        "text": "I would check the server logs, restart the application pod, and notify the team if it still doesn't work.",
        "label": "⚠️ Test Shallow Troubleshooting"
    },
    "scenario_strong": {
        "text": "First, I isolate the failure boundary using Prometheus metrics and Grafana dashboards to verify if the issue is CPU starvation, database connection pool exhaustion, or external API timeouts. Second, if error rates spike after a new release, I initiate an immediate canary rollback while preserving container memory dumps. Third, I examine pgbouncer metrics and Slow Query logs in PostgreSQL to identify locking deadlocks. Finally, we conduct a blameless post-mortem with automated regression tests to prevent recurrence.",
        "label": "✅ Test Strong Troubleshooting"
    }
}
