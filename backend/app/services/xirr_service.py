"""XIRR (Extended Internal Rate of Return) calculation service.

Uses Newton-Raphson method to find the rate r that satisfies:
    sum( cash_flow_i / (1 + r) ^ ((date_i - date_0).days / 365.0) ) = 0

Cash flow sign convention:
    - Negative = money going OUT (BUY, DEPOSIT, FEE, TAX)
    - Positive = money coming IN (SELL, DIVIDEND, INTEREST, WITHDRAWAL, BONUS)
"""
from datetime import datetime, date
from typing import List, Tuple, Optional
import logging

from app.models.transaction import TransactionType

logger = logging.getLogger(__name__)

# Type alias
CashFlow = Tuple[date, float]

# Transaction types that represent outflows (money leaving user's pocket)
OUTFLOW_TYPES = {
    TransactionType.BUY,
    TransactionType.DEPOSIT,
    TransactionType.FEE,
    TransactionType.TAX,
    TransactionType.TRANSFER_IN,
}

# Transaction types that represent inflows (money returning to user)
INFLOW_TYPES = {
    TransactionType.SELL,
    TransactionType.DIVIDEND,
    TransactionType.INTEREST,
    TransactionType.WITHDRAWAL,
    TransactionType.BONUS,
    TransactionType.TRANSFER_OUT,
}


def _try_newton(
    amounts: List[float],
    years: List[float],
    guess: float,
    max_iterations: int,
    tolerance: float,
) -> Optional[float]:
    """Run Newton-Raphson iteration with a given initial guess.

    Returns annualized return as a percentage, or None if it fails to converge.
    """
    rate = guess

    for _ in range(max_iterations):
        f_val = 0.0
        f_deriv = 0.0

        valid = True
        for amount, year in zip(amounts, years):
            base = 1 + rate
            if base <= 0:
                valid = False
                break
            denom = base ** year
            f_val += amount / denom
            f_deriv -= year * amount / (base * denom)

        if not valid:
            rate = abs(rate) * 0.5 + 0.01
            continue

        if abs(f_deriv) < 1e-14:
            return None

        new_rate = rate - f_val / f_deriv

        if abs(new_rate - rate) < tolerance:
            return round(new_rate * 100, 2)

        rate = new_rate

    return None


def calculate_xirr(
    cash_flows: List[CashFlow],
    guess: float = 0.1,
    max_iterations: int = 100,
    tolerance: float = 1e-7,
) -> Optional[float]:
    """Calculate XIRR for a series of cash flows.

    Args:
        cash_flows: List of (date, amount) tuples. Amounts follow
                    sign convention: negative=outflow, positive=inflow.
        guess: Initial guess for the rate (default 10%).
        max_iterations: Maximum Newton-Raphson iterations.
        tolerance: Convergence threshold.

    Returns:
        Annualized return rate as a percentage (e.g., 12.5 for 12.5%),
        or None if calculation fails to converge or is invalid.
    """
    if not cash_flows or len(cash_flows) < 2:
        return None

    # Need at least one positive and one negative cash flow
    has_positive = any(cf[1] > 0 for cf in cash_flows)
    has_negative = any(cf[1] < 0 for cf in cash_flows)
    if not (has_positive and has_negative):
        return None

    # Sort by date
    cash_flows = sorted(cash_flows, key=lambda x: x[0])
    d0 = cash_flows[0][0]

    # Year fractions from first date
    years = [(cf[0] - d0).days / 365.0 for cf in cash_flows]
    amounts = [cf[1] for cf in cash_flows]

    # Try primary guess
    result = _try_newton(amounts, years, guess, max_iterations, tolerance)
    if result is not None:
        return result

    # Retry with alternative guesses
    for alt_guess in [-0.5, 0.0, 0.5, 1.0, 2.0, 5.0]:
        if alt_guess == guess:
            continue
        result = _try_newton(amounts, years, alt_guess, max_iterations, tolerance)
        if result is not None:
            return result

    logger.warning("XIRR calculation failed to converge")
    return None


def build_cash_flows_from_transactions(
    transactions,
    current_value: float,
    current_date: Optional[date] = None,
) -> List[CashFlow]:
    """Build XIRR cash flows from an asset's transactions.

    Adds a terminal inflow for the current value of the holding.

    Args:
        transactions: List of Transaction model objects.
        current_value: Current market value of the asset.
        current_date: Date for the terminal value (defaults to today).

    Returns:
        List of (date, amount) tuples with correct sign convention.
    """
    if current_date is None:
        current_date = date.today()

    cash_flows: List[CashFlow] = []

    for txn in transactions:
        txn_date = (
            txn.transaction_date.date()
            if isinstance(txn.transaction_date, datetime)
            else txn.transaction_date
        )
        amount = txn.total_amount or 0
        fees = txn.fees or 0
        taxes = txn.taxes or 0

        if txn.transaction_type in OUTFLOW_TYPES:
            # Outflow: total cost including fees/taxes
            cash_flows.append((txn_date, -(amount + fees + taxes)))
        elif txn.transaction_type in INFLOW_TYPES:
            # Inflow: net proceeds after fees/taxes
            cash_flows.append((txn_date, amount - fees - taxes))
        # SPLIT and other types don't involve cash flow — skip

    # Terminal value: if the asset still has value, treat it as a virtual sell
    if current_value and current_value > 0:
        cash_flows.append((current_date, current_value))

    return cash_flows


def calculate_asset_xirr(
    transactions, current_value: float
) -> Optional[float]:
    """Convenience function: build cash flows and calculate XIRR for an asset."""
    cash_flows = build_cash_flows_from_transactions(transactions, current_value)
    return calculate_xirr(cash_flows)
