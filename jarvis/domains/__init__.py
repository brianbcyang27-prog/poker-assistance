"""JARVIS v10 Domains — department-based agent organization.

Public surface: Domain/DomainInfo metadata, domain base classes,
the three new standalone domains, and the DomainRegistry.
"""

from .base import DomainMaster, DomainMember, DomainWorker
from .education import (
    AssessmentWorker,
    CurriculumWorker,
    EducationMaster,
    ExplainerWorker,
    TutorWorker,
)
from .finance import (
    BudgetWorker,
    ExpenseWorker,
    FinanceMaster,
    InvestmentsWorker,
    TaxWorker,
)
from .models import (
    DOMAIN_INFO,
    Domain,
    DomainInfo,
    domain_by_alias,
    domain_from_member_id,
    user_domains,
)
from .registry import DomainRegistry
from .studio import (
    AnimationWorker,
    FabricationWorker,
    ModelingWorker,
    RenderingWorker,
    StudioMaster,
)

__all__ = [
    "AssessmentWorker",
    "AnimationWorker",
    "BudgetWorker",
    "CurriculumWorker",
    "DOMAIN_INFO",
    "Domain",
    "DomainInfo",
    "DomainMaster",
    "DomainMember",
    "DomainRegistry",
    "DomainWorker",
    "EducationMaster",
    "ExpenseWorker",
    "ExplainerWorker",
    "FabricationWorker",
    "FinanceMaster",
    "InvestmentsWorker",
    "ModelingWorker",
    "RenderingWorker",
    "StudioMaster",
    "TaxWorker",
    "TutorWorker",
    "domain_by_alias",
    "domain_from_member_id",
    "user_domains",
]
