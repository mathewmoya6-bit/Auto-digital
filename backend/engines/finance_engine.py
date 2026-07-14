"""
Finance Engine - Auto-D Kenya
Professional loan amortization and financing calculations
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class LoanResult:
    """Loan calculation result"""
    monthly_payment: float = 0.0
    total_payment: float = 0.0
    total_interest: float = 0.0
    loan_balance: float = 0.0
    amortization_schedule: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class FinanceResult:
    """Complete financing result"""
    loan: LoanResult
    annual_payment: float = 0.0
    interest_rate: float = 0.0
    loan_term: int = 0
    deposit_amount: float = 0.0
    loan_amount: float = 0.0


# ─── FINANCE ENGINE ────────────────────────────────────────────────

class FinanceEngine:
    """Professional finance and loan calculation engine"""
    
    @staticmethod
    def calculate_loan(
        principal: float,
        annual_rate: float,
        years: int,
        payment_frequency: str = "monthly"
    ) -> LoanResult:
        """
        Calculate loan amortization.
        
        Args:
            principal: Loan amount
            annual_rate: Annual interest rate (%)
            years: Loan term in years
            payment_frequency: monthly, quarterly, yearly
        
        Returns:
            LoanResult with amortization schedule
        """
        if years <= 0 or principal <= 0:
            return LoanResult()
        
        annual_rate_decimal = annual_rate / 100
        
        # Calculate number of payments
        payments_per_year = {
            "monthly": 12,
            "quarterly": 4,
            "yearly": 1
        }.get(payment_frequency, 12)
        
        num_payments = int(years * payments_per_year)
        
        if annual_rate_decimal == 0:
            monthly_payment = principal / num_payments if num_payments > 0 else 0
        else:
            rate_per_period = annual_rate_decimal / payments_per_year
            monthly_payment = principal * (
                rate_per_period * (1 + rate_per_period) ** num_payments
            ) / ((1 + rate_per_period) ** num_payments - 1)
        
        # Build amortization schedule
        schedule = []
        remaining_balance = principal
        
        for period in range(1, num_payments + 1):
            interest_payment = remaining_balance * rate_per_period
            principal_payment = monthly_payment - interest_payment
            remaining_balance -= principal_payment
            
            schedule.append({
                "period": period,
                "payment": round(monthly_payment, 2),
                "principal": round(principal_payment, 2),
                "interest": round(interest_payment, 2),
                "balance": round(max(remaining_balance, 0), 2)
            })
        
        total_payment = monthly_payment * num_payments
        total_interest = total_payment - principal
        
        return LoanResult(
            monthly_payment=round(monthly_payment, 2),
            total_payment=round(total_payment, 2),
            total_interest=round(total_interest, 2),
            loan_balance=round(max(remaining_balance, 0), 2),
            amortization_schedule=schedule
        )
    
    @staticmethod
    def calculate_financing(
        vehicle_price: float,
        deposit_percent: float,
        annual_rate: float,
        years: int,
        payment_frequency: str = "monthly"
    ) -> FinanceResult:
        """Calculate complete financing details"""
        deposit_amount = vehicle_price * (deposit_percent / 100)
        loan_amount = vehicle_price - deposit_amount
        
        loan_result = FinanceEngine.calculate_loan(
            principal=loan_amount,
            annual_rate=annual_rate,
            years=years,
            payment_frequency=payment_frequency
        )
        
        return FinanceResult(
            loan=loan_result,
            annual_payment=round(loan_result.monthly_payment * 12, 2),
            interest_rate=annual_rate,
            loan_term=years,
            deposit_amount=round(deposit_amount, 2),
            loan_amount=round(loan_amount, 2)
        )


def calculate_loan_amortization(
    principal: float,
    annual_rate: float,
    years: int
) -> Dict[str, Any]:
    """Convenience function for loan calculation"""
    result = FinanceEngine.calculate_loan(
        principal=principal,
        annual_rate=annual_rate,
        years=years
    )
    
    return {
        "monthly_payment": result.monthly_payment,
        "total_payment": result.total_payment,
        "total_interest": result.total_interest,
        "loan_balance": result.loan_balance,
        "amortization_schedule": result.amortization_schedule[:12]  # First 12 months
    }


def calculate_interest(
    principal: float,
    annual_rate: float,
    years: int
) -> Dict[str, Any]:
    """Simple interest calculation"""
    result = FinanceEngine.calculate_loan(
        principal=principal,
        annual_rate=annual_rate,
        years=years
    )
    
    return {
        "total_interest": result.total_interest,
        "total_payment": result.total_payment,
        "monthly_payment": result.monthly_payment
    }
