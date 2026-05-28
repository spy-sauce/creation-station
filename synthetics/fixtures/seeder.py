# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Idempotent seeder for synthetic candidates.

Loads synthetic candidate definitions and upserts them into Postgres.
Safe to call on every backend boot — no duplicate rows, no constraint violations.

Synthetic candidates use UUIDv5 under the DNS namespace for deterministic IDs.
Detection: backend.synthetics.known_ids.is_synthetic(candidate_id).

Contract: NUTRIENTS.md § I.1 Synthetic Candidate Isolation (as amended by iter-6)
Contract: HYPHA-SYNTHETICS-FIXTURES.md Acceptance Criteria
"""

import uuid
from pathlib import Path
from typing import Any

import structlog
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.models.discovery import Candidate, RemotePreference
from backend.synthetics.known_ids import SYNTHETIC_CANDIDATE_IDS, SYNTHETIC_CANDIDATE_ID_SET

logger = structlog.get_logger(__name__)

# Path to candidates YAML fixture
CANDIDATES_YAML = Path(__file__).parent / "candidates.yaml"

# UUIDv5 namespace for synthetic candidates
# Derivation: uuid.uuid5(uuid.NAMESPACE_DNS, "synthetic-" + slug)
# Contract: NUTRIENTS.md § I.1
SYNTHETIC_NAMESPACE = uuid.NAMESPACE_DNS


def get_synthetic_id(slug: str) -> uuid.UUID:
    """
    Generate deterministic UUIDv5 for a synthetic candidate.

    Handles both slug formats:
    - With prefix: "synthetic-jr-engineer" → uses as-is
    - Without prefix: "jr-engineer" → adds "synthetic-" prefix

    Args:
        slug: Candidate slug (with or without "synthetic-" prefix)

    Returns:
        Deterministic UUID in the synthetic namespace

    Contract: NUTRIENTS.md § I.1
    """
    # Normalize slug - ensure it has the synthetic- prefix
    if slug.startswith("synthetic-"):
        name = slug
    else:
        name = f"synthetic-{slug}"
    return uuid.uuid5(SYNTHETIC_NAMESPACE, name)


# Inline synthetic candidate definitions
# These are the canonical definitions used when candidates.yaml is not available
# Contract: HYPHA-SYNTHETICS-FIXTURES.md § Notes
SYNTHETIC_CANDIDATES: list[dict[str, Any]] = [
    {
        "slug": "jr-engineer",
        "name": "Alex Chen",
        "email": "synthetic-jr@talent-agent.test",
        "resume_text": """# Alex Chen
## Full-Stack Developer

Entry-level software engineer with 2 years of experience building web applications.
Recent CS graduate from NYU with a passion for clean code and user experience.

### Technical Skills
- **Languages:** TypeScript, JavaScript, Python, SQL
- **Frontend:** React, Next.js, Tailwind CSS, HTML5, CSS3
- **Backend:** Node.js, Express, FastAPI, REST APIs
- **Databases:** PostgreSQL, MongoDB, Redis
- **Tools:** Git, Docker, VS Code, Postman, Figma

### Experience

**Software Engineer** | StartupXYZ | Jan 2024 - Present
- Built responsive React components serving 10K+ daily users
- Implemented REST APIs using Node.js and Express
- Collaborated with design team to improve UX patterns
- Reduced page load time by 40% through code optimization

**Software Engineering Intern** | TechCorp | Summer 2023
- Developed internal tools using React and TypeScript
- Wrote unit tests achieving 85% code coverage
- Participated in code reviews and agile ceremonies

### Education
**B.S. Computer Science** | New York University | 2023
- GPA: 3.7
- Relevant coursework: Data Structures, Algorithms, Web Development, Databases

### Projects
**TaskFlow** - React/Node.js task management app with real-time updates
**WeatherNow** - TypeScript weather dashboard consuming public APIs
""",
        "linkedin_url": "https://linkedin.com/in/synthetic-alex-chen",
        "github_url": "https://github.com/synthetic-alexchen",
        "personal_context": "Looking for full-stack roles at growth-stage startups in NYC. Open to hybrid work. Interested in fintech and developer tools. Values mentorship and learning opportunities.",
        "target_locations": ["New York, NY", "Brooklyn, NY", "Jersey City, NJ"],
        "remote_preference": RemotePreference.HYBRID,
        "min_compensation": 80000,
        "excluded_companies": ["BigTech Corp", "Legacy Systems Inc"],
        "excluded_industries": ["gambling", "tobacco"],
    },
    {
        "slug": "senior-ml",
        "name": "Dr. Maya Patel",
        "email": "synthetic-ml@talent-agent.test",
        "resume_text": """# Dr. Maya Patel
## Staff Machine Learning Engineer

8+ years experience building production ML systems at scale. PhD in Machine Learning
from Stanford. Led teams of 5-12 engineers. Published researcher with 15+ papers.

### Technical Skills
- **ML Frameworks:** PyTorch, TensorFlow, JAX, Hugging Face Transformers
- **MLOps:** MLflow, Kubeflow, Weights & Biases, Vertex AI
- **Infrastructure:** Kubernetes, Ray, Spark, distributed training
- **Languages:** Python, C++, Rust, SQL
- **Cloud:** GCP (Expert), AWS (Advanced), Azure (Intermediate)

### Experience

**Staff ML Engineer** | Anthropic | 2021 - Present
- Led team of 8 engineers on core model training infrastructure
- Designed distributed training system handling 1000+ GPU clusters
- Reduced training costs by 35% through optimization techniques
- Mentored 12 engineers across ML and infrastructure teams

**Senior ML Engineer** | Google Brain | 2018 - 2021
- Core contributor to TensorFlow model optimization toolkit
- Built recommendation systems serving 100M+ users
- Published 5 papers at NeurIPS, ICML, and ICLR
- Promoted to Staff track within 2 years

**ML Engineer** | Facebook AI Research | 2016 - 2018
- Developed computer vision models for content understanding
- Optimized model inference latency by 60%
- Collaborated with research scientists on novel architectures

### Education
**Ph.D. Machine Learning** | Stanford University | 2016
- Dissertation: "Efficient Training Methods for Large Neural Networks"
- Advisor: Dr. Andrew Ng

**B.S. Computer Science, Mathematics** | MIT | 2012

### Publications
- "Scaling Laws for Neural Language Models" - NeurIPS 2023
- "Efficient Fine-tuning of Large Language Models" - ICML 2022
- 13 additional publications (h-index: 24)

### Leadership
- Tech lead for 8-person ML infrastructure team
- Mentor in Stanford AI mentorship program
- Conference reviewer: NeurIPS, ICML, ICLR
""",
        "linkedin_url": "https://linkedin.com/in/synthetic-maya-patel",
        "github_url": "https://github.com/synthetic-mayapatel",
        "personal_context": "Looking for Staff+ roles at AI labs or top-tier tech companies. Strongly prefer remote work from Bay Area home. Interested in foundation models, alignment research, and ML systems. Minimum equity consideration important at this level.",
        "target_locations": ["San Francisco, CA", "Palo Alto, CA", "Remote"],
        "remote_preference": RemotePreference.REMOTE_ONLY,
        "min_compensation": 250000,
        "excluded_companies": ["Defense contractors"],
        "excluded_industries": ["defense", "surveillance", "adtech"],
    },
    {
        "slug": "mid-product",
        "name": "Jordan Rivera",
        "email": "synthetic-pm@talent-agent.test",
        "resume_text": """# Jordan Rivera
## Senior Product Manager

5 years of product management experience in B2B SaaS. Data-driven PM with strong
technical background. Led products from 0-1 and scaled to $10M+ ARR.

### Skills
- **Product:** Roadmapping, user research, A/B testing, analytics, GTM strategy
- **Technical:** SQL, Python basics, API design, system architecture understanding
- **Tools:** Amplitude, Mixpanel, Figma, Jira, Notion, Miro
- **Methodologies:** Agile, Scrum, Jobs-to-be-Done, Double Diamond

### Experience

**Senior Product Manager** | DataStack (Series B, $50M raised) | 2022 - Present
- Own data pipeline product serving 200+ enterprise customers
- Grew product revenue from $3M to $12M ARR in 18 months
- Led cross-functional team of 8 engineers, 2 designers
- Shipped 15 major features with 90%+ adoption rate
- Reduced customer churn by 25% through user research insights

**Product Manager** | CloudFlow | 2020 - 2022
- Managed developer tools product with 50K MAU
- Conducted 100+ user interviews to inform product strategy
- Launched API marketplace generating $2M incremental revenue
- Improved NPS from 32 to 58 through UX improvements

**Associate Product Manager** | TechStartup (Acq. by CloudFlow) | 2019 - 2020
- First PM hire, built product process from scratch
- Defined product vision and initial roadmap
- Collaborated directly with founders and engineering

### Education
**MBA** | Kellogg School of Management | 2019
- Concentration: Technology & Innovation

**B.S. Industrial Engineering** | Georgia Tech | 2015

### Certifications
- Pragmatic Marketing Certified (PMC III)
- Certified Scrum Product Owner (CSPO)

### Side Projects
- Product management newsletter with 5K subscribers
- Speaker at ProductCon 2023: "Data-Driven Product Decisions"
""",
        "linkedin_url": "https://linkedin.com/in/synthetic-jordan-rivera",
        "github_url": None,
        "personal_context": "Looking for Senior PM or Director roles at growth-stage B2B SaaS companies. Fully remote preferred. Interested in data infrastructure, developer tools, and AI products. Values strong engineering culture and clear product-engineering collaboration.",
        "target_locations": ["Remote"],
        "remote_preference": RemotePreference.REMOTE_ONLY,
        "min_compensation": 150000,
        "excluded_companies": [],
        "excluded_industries": ["crypto", "web3", "NFT"],
    },
]


def _load_candidates_from_yaml() -> list[dict[str, Any]] | None:
    """
    Load synthetic candidates from YAML file if available.

    Returns:
        List of candidate definitions, or None if file not found
    """
    if not CANDIDATES_YAML.exists():
        return None

    with CANDIDATES_YAML.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "candidates" not in data:
        return None

    return data["candidates"]


def _build_candidate(definition: dict[str, Any]) -> Candidate:
    """
    Build a Candidate ORM instance from a fixture definition.

    Handles both formats:
    - Inline format: flat dict with direct fields
    - YAML format: may have nested identity_context dict

    Args:
        definition: Dict with candidate fields including 'slug'

    Returns:
        Candidate instance with deterministic UUID
    """
    slug = definition["slug"]
    candidate_id = get_synthetic_id(slug)

    # Extract identity_context if present (YAML format)
    identity_ctx = definition.get("identity_context", {})

    # Handle remote_preference - check both top-level and identity_context
    remote_pref = (
        definition.get("remote_preference")
        or identity_ctx.get("remote_preference")
        or "flexible"
    )
    if isinstance(remote_pref, str):
        remote_pref = RemotePreference(remote_pref)

    # Handle min_compensation - check both top-level and identity_context
    min_comp = (
        definition.get("min_compensation")
        or identity_ctx.get("target_salary_min")
    )

    return Candidate(
        id=candidate_id,
        name=definition["name"],
        email=definition["email"],
        resume_text=definition.get("resume_text"),
        linkedin_url=definition.get("linkedin_url"),
        github_url=definition.get("github_url"),
        personal_context=definition.get("personal_context"),
        target_locations=definition.get("target_locations", []),
        remote_preference=remote_pref,
        min_compensation=min_comp,
        excluded_companies=definition.get("excluded_companies", []),
        excluded_industries=definition.get("excluded_industries", []),
    )


async def _upsert_candidate(session: AsyncSession, candidate: Candidate) -> bool:
    """
    Upsert a synthetic candidate into the database.

    Checks if candidate exists by UUID. If exists, skips (idempotent).
    If not exists, inserts.

    Args:
        session: SQLAlchemy async session
        candidate: Candidate ORM instance to upsert

    Returns:
        True if inserted, False if already existed
    """
    # Check if candidate already exists
    result = await session.execute(
        select(Candidate).where(Candidate.id == candidate.id)
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        logger.debug(
            "synthetic.candidate.skip",
            candidate_id=str(candidate.id),
            slug=candidate.email.split("@")[0].replace("synthetic-", ""),
            reason="already_exists",
        )
        return False

    session.add(candidate)
    return True


async def seed() -> None:
    """
    Seed synthetic candidates into the database.

    Idempotent: safe to call on every backend boot.
    No duplicate rows, no constraint violations.

    Loads candidates from:
    1. candidates.yaml if present (allows external fixture management)
    2. Inline SYNTHETIC_CANDIDATES as fallback

    Contract: HYPHA-SYNTHETICS-FIXTURES.md Acceptance Criteria
    """
    # Try to load from YAML first, fall back to inline definitions
    yaml_candidates = _load_candidates_from_yaml()
    if yaml_candidates:
        candidate_defs = yaml_candidates
        source = "yaml"
    else:
        candidate_defs = SYNTHETIC_CANDIDATES
        source = "inline"

    logger.info(
        "synthetic.seed.start",
        count=len(candidate_defs),
        source=source,
    )

    inserted = 0
    skipped = 0

    async with AsyncSessionLocal() as session:
        for definition in candidate_defs:
            candidate = _build_candidate(definition)
            was_inserted = await _upsert_candidate(session, candidate)
            if was_inserted:
                inserted += 1
                logger.info(
                    "synthetic.candidate.created",
                    candidate_id=str(candidate.id),
                    name=candidate.name,
                    email=candidate.email,
                )
            else:
                skipped += 1

        await session.commit()

        # Self-verify: ensure seeded UUIDs match known_ids constants
        # Contract: NUTRIENTS.md § I.1 (as amended by iter-6)
        verify_result = await session.execute(
            select(Candidate.id).where(
                Candidate.id.in_([str(uid) for uid in SYNTHETIC_CANDIDATE_ID_SET])
            )
        )
        seeded_ids = {row[0] for row in verify_result.fetchall()}

        if seeded_ids != SYNTHETIC_CANDIDATE_ID_SET:
            missing = SYNTHETIC_CANDIDATE_ID_SET - seeded_ids
            unexpected = seeded_ids - SYNTHETIC_CANDIDATE_ID_SET
            logger.error(
                "seeder.verify_failed",
                missing=str(missing),
                unexpected=str(unexpected),
                message="Synthetic seeding produced unexpected UUIDs",
            )
            raise RuntimeError(
                f"synthetic seeding produced unexpected UUIDs: "
                f"missing={missing}, unexpected={unexpected}"
            )

        logger.info(
            "seeder.verify_passed",
            verified_count=len(seeded_ids),
        )

    logger.info(
        "synthetic.seed.complete",
        inserted=inserted,
        skipped=skipped,
        total=len(candidate_defs),
    )


async def get_synthetic_candidate_ids() -> list[uuid.UUID]:
    """
    Get all synthetic candidate UUIDs.

    Returns:
        List of UUIDv5 identifiers for synthetic candidates
    """
    return [get_synthetic_id(c["slug"]) for c in SYNTHETIC_CANDIDATES]


async def is_synthetic_candidate(candidate_id: uuid.UUID) -> bool:
    """
    Check if a candidate ID belongs to a synthetic candidate.

    Detection: UUIDv5 under DNS namespace produces distinctive pattern.

    Args:
        candidate_id: UUID to check

    Returns:
        True if this is a synthetic candidate ID
    """
    synthetic_ids = await get_synthetic_candidate_ids()
    return candidate_id in synthetic_ids
