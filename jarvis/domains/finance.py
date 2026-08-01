"""Finance domain — money management (new in v10; elevated from a worker)."""

from .base import DomainMaster, DomainWorker
from .models import Domain


class BudgetWorker(DomainWorker):
    """Budget planning, forecasting, and allocation."""

    def get_system_prompt(self) -> str:
        return (
            "You are the Budget Specialist. Build and maintain budgets: categorize "
            "spending, set allocations and limits, forecast monthly/annual totals, "
            "and flag overruns with concrete adjustments."
        )


class ExpenseWorker(DomainWorker):
    """Expense tracking, categorization, and reporting."""

    def get_system_prompt(self) -> str:
        return (
            "You are the Expense Tracker. Record and categorize expenses, spot "
            "spending trends, and produce clear reports. Always note the currency "
            "and the date range of any figures you report."
        )


class InvestmentsWorker(DomainWorker):
    """Investment analysis and portfolio review."""

    def get_system_prompt(self) -> str:
        return (
            "You are the Investments Advisor. Review portfolios, explain risk/return "
            "tradeoffs, and research asset classes. You advise — you never guarantee "
            "returns. Clearly label any estimate as an estimate."
        )


class TaxWorker(DomainWorker):
    """Tax planning and filing preparation."""

    def get_system_prompt(self) -> str:
        return (
            "You are the Tax Specialist. Prepare tax estimates, organize deductions, "
            "and explain filing requirements. Flag anything that needs a licensed "
            "professional; never give legal advice."
        )


class FinanceMaster(DomainMaster):
    """Finance domain master — head of money management."""

    def __init__(self):
        super().__init__(Domain.FINANCE, "finance.master")

    @property
    def name(self) -> str:
        return "Finance Master"

    @property
    def title(self) -> str:
        return "Head of Money Management"

    def _build_members(self) -> None:
        self.register_member(BudgetWorker(Domain.FINANCE, "finance.budget"))
        self.register_member(ExpenseWorker(Domain.FINANCE, "finance.expense"))
        self.register_member(InvestmentsWorker(Domain.FINANCE, "finance.investments"))
        self.register_member(TaxWorker(Domain.FINANCE, "finance.tax"))
