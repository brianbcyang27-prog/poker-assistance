"""Domain model — v10 departments (JARVIS_V10_MASTER_PLAN §2.3).

Work in JARVIS v10 is organized into Domains (departments), not poker cards.
This module defines the canonical Domain enum and its metadata table.

Compat-first rule (§3.1): card classes (Suit/Rank/King/Worker) remain as
deprecated aliases. Domain introduces a parallel identity scheme via
`member_id`; `card_id` remains available on domain members as a compat alias.
"""

from dataclasses import dataclass
from enum import StrEnum


class Domain(StrEnum):
    """The seven JARVIS v10 domains (System is internal, not a user domain)."""

    ENGINEERING = "engineering"
    EDUCATION = "education"
    RESEARCH = "research"
    STUDIO = "studio"
    FINANCE = "finance"
    PERSONAL = "personal"
    SYSTEM = "system"

    @property
    def is_user_domain(self) -> bool:
        """User-facing domains are everything except internal System services."""
        return self is not Domain.SYSTEM

    @property
    def label(self) -> str:
        """Human-readable domain label."""
        return DOMAIN_INFO[self].label

    @property
    def master_member_id(self) -> str:
        """Canonical member_id of this domain's master."""
        return f"{self.value}.master"


@dataclass(frozen=True)
class DomainInfo:
    """Static metadata for a domain.

    `worker_member_ids` lists the canonical workers of a domain. For domains
    backed by an existing card King (engineering/research/personal/system) the
    ids are the King's worker card_ids (compat aliases); the runtime registry
    pulls the authoritative member list from the attached King.
    """

    domain: Domain
    label: str
    description: str
    aliases: tuple[str, ...] = ()
    worker_member_ids: tuple[str, ...] = ()
    color: str = "#00d4ff"
    internal: bool = False

    @property
    def is_user_domain(self) -> bool:
        return not self.internal


#: Canonical metadata for all seven domains (§2.3 table).
DOMAIN_INFO: dict[Domain, DomainInfo] = {
    Domain.ENGINEERING: DomainInfo(
        domain=Domain.ENGINEERING,
        label="Engineering",
        description=(
            "Software and hardware engineering: architecture, backend, frontend, "
            "testing, docs, accessibility, CAD, PCB, embedded, mechanical."
        ),
        aliases=("engineering", "eng", "dev", "software", "build", "code"),
        worker_member_ids=(
            "♠Q",
            "♠J",
            "♠10",
            "♠9",
            "♠8",
            "♠7",
            "♠6",
            "♠5",
            "♠4",
            "♠4M",
            "♠3",
            "♠3T",
            "♠2",
        ),
        color="#00d4ff",
    ),
    Domain.EDUCATION: DomainInfo(
        domain=Domain.EDUCATION,
        label="Education",
        description=(
            "Learning and teaching: tutoring, curriculum design, assessment, "
            "and concept explanation."
        ),
        aliases=("education", "edu", "learning", "tutor", "study", "teach"),
        worker_member_ids=(
            "education.tutor",
            "education.curriculum",
            "education.assessment",
            "education.explainer",
        ),
        color="#a78bfa",
    ),
    Domain.RESEARCH: DomainInfo(
        domain=Domain.RESEARCH,
        label="Research",
        description=(
            "Discovery and analysis: web research, documentation, and "
            "fact-checking (fact checking becomes a shared global service in M2)."
        ),
        aliases=("research", "res", "web research", "analyze", "discovery"),
        worker_member_ids=("♦Q", "♦J", "♦10"),
        color="#ffaa00",
    ),
    Domain.STUDIO: DomainInfo(
        domain=Domain.STUDIO,
        label="3D",
        description=(
            "3D creation and fabrication: modeling, rendering, animation, and "
            "fabrication, powered by the existing CAD/Blender assets."
        ),
        aliases=("3d", "3d studio", "studio", "cad", "blender", "modeling", "design"),
        worker_member_ids=(
            "studio.modeling",
            "studio.rendering",
            "studio.animation",
            "studio.fabrication",
        ),
        color="#f97316",
    ),
    Domain.FINANCE: DomainInfo(
        domain=Domain.FINANCE,
        label="Finance",
        description=(
            "Money management: budgeting, expense tracking, investments, and "
            "tax planning. Elevated from a worker to a first-class domain."
        ),
        aliases=("finance", "money", "budget", "accounting", "financial"),
        worker_member_ids=(
            "finance.budget",
            "finance.expense",
            "finance.investments",
            "finance.tax",
        ),
        color="#10b981",
    ),
    Domain.PERSONAL: DomainInfo(
        domain=Domain.PERSONAL,
        label="Personal",
        description=("Personal organization: calendar, email, tasks, and scheduling."),
        aliases=("personal", "assistant", "organize", "calendar"),
        worker_member_ids=("♥Q", "♥J", "♥10", "♥9"),
        color="#ff4466",
    ),
    Domain.SYSTEM: DomainInfo(
        domain=Domain.SYSTEM,
        label="System",
        description=(
            "JARVIS Core Services — files, terminal, and applications. "
            "Internal infrastructure, not a user-facing domain."
        ),
        aliases=("system", "sys", "internal", "core services"),
        worker_member_ids=("♣Q", "♣J", "♣10"),
        color="#00ff88",
        internal=True,
    ),
}


def domain_by_alias(name: str) -> Domain | None:
    """Resolve a Domain from a label or alias (case-insensitive).

    Matches the domain value, label, and any alias. Returns None when the
    name matches nothing.
    """
    if not name:
        return None
    lowered = name.strip().lower()
    for domain, info in DOMAIN_INFO.items():
        if domain.value == lowered or info.label.lower() == lowered or lowered in info.aliases:
            return domain
    return None


def user_domains() -> list[Domain]:
    """All user-facing domains in canonical order (System excluded)."""
    return [d for d in Domain if d.is_user_domain]


def domain_from_member_id(member_id: str) -> Domain | None:
    """Resolve the owning domain of a member_id (e.g. 'education.tutor')."""
    if not member_id:
        return None
    for domain in Domain:
        if member_id.startswith(f"{domain.value}."):
            return domain
    return None
