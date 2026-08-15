"""DomainRegistry — single owner of the domain → master → members mapping.

King-backed domains (engineering, research, personal, system) attach their
existing card King for execution and register its workers as members; the
three new domains (education, studio, finance) build standalone masters.
"""

from ..agents.kings.base import BaseKing
from .base import DomainMaster
from .education import EducationMaster
from .finance import FinanceMaster
from .models import Domain, user_domains
from .studio import StudioMaster


class DomainRegistry:
    """Builds and serves domain masters, backed by card Kings where they exist."""

    def __init__(self):
        self._masters: dict[Domain, DomainMaster] = {
            domain: self._build_master(domain) for domain in Domain
        }

    def attach_kings(self, kings: list[BaseKing]) -> None:
        """Attach card Kings to their domains and register their workers."""
        for king in kings:
            domain = self._domain_for_king(king)
            if domain is None:
                continue
            master = self._ensure_master(domain)
            master.attach_king(king)
            for worker in king.get_all_workers():
                master.register_member(worker)

    def _domain_for_king(self, king) -> Domain | None:
        suit_to_domain = {
            "spades": Domain.ENGINEERING,
            "hearts": Domain.PERSONAL,
            "diamonds": Domain.RESEARCH,
            "clubs": Domain.SYSTEM,
        }
        if king.suit is None:
            return None
        return suit_to_domain.get(king.suit.value)

    def _ensure_master(self, domain: Domain) -> DomainMaster:
        if domain not in self._masters:
            self._masters[domain] = self._build_master(domain)
        return self._masters[domain]

    def _build_master(self, domain: Domain) -> DomainMaster:
        if domain is Domain.EDUCATION:
            return EducationMaster()
        if domain is Domain.STUDIO:
            return StudioMaster()
        if domain is Domain.FINANCE:
            return FinanceMaster()
        return DomainMaster(domain, domain.master_member_id)

    def get(self, domain: Domain | str) -> DomainMaster | None:
        """Get a master by Domain or by value/alias string."""
        if isinstance(domain, str):
            try:
                resolved = Domain(domain)
            except ValueError:
                from .models import domain_by_alias

                resolved = domain_by_alias(domain)
            domain = resolved
        if domain is None:
            return None
        return self._masters.get(domain)

    def all(self) -> list[DomainMaster]:
        """All domain masters in canonical order (including System)."""
        return [self._masters[d] for d in Domain if d in self._masters]

    def all_user(self) -> list[DomainMaster]:
        """User-facing domain masters in canonical order (System excluded)."""
        return [self._masters[d] for d in user_domains() if d in self._masters]

    def get_member(self, member_id: str):
        """Find a member across all domains by member_id."""
        for master in self._masters.values():
            member = master.get_member(member_id)
            if member is not None:
                return member
        return None

    def total_members(self) -> int:
        return sum(len(m.get_all_members()) for m in self._masters.values())
