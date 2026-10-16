"""Tool B: Charge Checker - Verify port/CFS charges against tariff rates."""
from typing import List, Dict, Tuple
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from enum import Enum
from .retrieval import DataLoader


class ChargeFlag(Enum):
    """Types of charge issues that can be flagged."""
    WRONG_RATE = "wrong_rate"
    WRONG_FREE_DAYS = "wrong_free_days"
    DUPLICATE_CHARGE = "duplicate_charge"
    NOT_IN_TARIFF = "not_in_tariff"
    WRONG_GST = "wrong_gst"
    WRONG_CURRENCY = "wrong_currency"


@dataclass
class ChargeItem:
    """A single charge from an invoice."""
    description: str
    quantity: float
    unit_rate: Decimal
    total: Decimal
    tariff_ref: str = ""
    gst_rate: Decimal = Decimal("18")


@dataclass
class ChargeIssue:
    """A flagged issue with a charge."""
    flag_type: ChargeFlag
    charge_description: str
    billed_amount: Decimal
    expected_amount: Decimal
    tariff_ref: str
    message: str


class ChargeChecker:
    """Validates charges against tariff rates."""

    def __init__(self, gst_rate: Decimal = Decimal("18")):
        """Initialize charge checker.

        Args:
            gst_rate: Default GST rate (as percentage)
        """
        self.tariff_rates = DataLoader.load_tariff_rates()
        self.rules = DataLoader.load_rules()
        self.gst_rate = Decimal(gst_rate)
        self.checked_charges = {}

    def check_invoice(self, invoice: Dict) -> Dict:
        """Check entire invoice against tariff rates.

        Args:
            invoice: Invoice data with line items and port/CFS info

        Returns:
            Analysis results with flagged issues
        """
        charges = invoice.get("charges", [])
        port = invoice.get("port", "")
        cfs = invoice.get("cfs", "")

        issues = []
        total_variance = Decimal("0")

        for charge in charges:
            charge_issues, variance = self._check_charge(
                charge, port, cfs
            )
            issues.extend(charge_issues)
            total_variance += variance

        # Check for duplicate charges
        duplicate_issues = self._check_duplicates(charges)
        issues.extend(duplicate_issues)

        return {
            "invoice_id": invoice.get("id", ""),
            "status": "FLAGGED" if issues else "OK",
            "total_issues": len(issues),
            "issues": [
                {
                    "type": issue.flag_type.value,
                    "charge": issue.charge_description,
                    "billed": float(issue.billed_amount),
                    "expected": float(issue.expected_amount),
                    "tariff_ref": issue.tariff_ref,
                    "message": issue.message
                }
                for issue in issues
            ],
            "total_variance": float(total_variance)
        }

    def _check_charge(self, charge: Dict, port: str, cfs: str) -> Tuple[List[ChargeIssue], Decimal]:
        """Check a single charge line item.

        Args:
            charge: Charge line item
            port: Port/CFS location
            cfs: CFS facility identifier

        Returns:
            Tuple of (issues list, variance amount)
        """
        issues = []
        variance = Decimal("0")

        description = charge.get("description", "")
        billed = Decimal(str(charge.get("amount", 0)))
        tariff_ref = charge.get("tariff_ref", "")

        # Check if charge is in tariff
        if not tariff_ref:
            issues.append(ChargeIssue(
                flag_type=ChargeFlag.NOT_IN_TARIFF,
                charge_description=description,
                billed_amount=billed,
                expected_amount=Decimal("0"),
                tariff_ref="UNKNOWN",
                message=f"Charge '{description}' has no tariff reference"
            ))
            return issues, billed

        # Get expected rate from tariff
        expected = self._get_tariff_rate(tariff_ref, port)

        if expected is None:
            issues.append(ChargeIssue(
                flag_type=ChargeFlag.NOT_IN_TARIFF,
                charge_description=description,
                billed_amount=billed,
                expected_amount=Decimal("0"),
                tariff_ref=tariff_ref,
                message=f"Tariff reference {tariff_ref} not found in rate card"
            ))
            return issues, billed

        # Check rate matches
        if billed != expected:
            variance = billed - expected
            issues.append(ChargeIssue(
                flag_type=ChargeFlag.WRONG_RATE,
                charge_description=description,
                billed_amount=billed,
                expected_amount=expected,
                tariff_ref=tariff_ref,
                message=f"Rate mismatch: billed {billed}, expected {expected}"
            ))

        # Check GST calculation
        gst_issues, gst_variance = self._check_gst(charge, expected)
        issues.extend(gst_issues)
        variance += gst_variance

        return issues, variance

    def _check_gst(self, charge: Dict, base_amount: Decimal) -> Tuple[List[ChargeIssue], Decimal]:
        """Check GST calculation on a charge.

        Args:
            charge: Charge line item
            base_amount: Base amount before GST

        Returns:
            Tuple of (issues, variance)
        """
        issues = []
        variance = Decimal("0")

        billed_gst = Decimal(str(charge.get("gst", 0)))
        expected_gst = (base_amount * self.gst_rate / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        if billed_gst != expected_gst:
            variance = billed_gst - expected_gst
            issues.append(ChargeIssue(
                flag_type=ChargeFlag.WRONG_GST,
                charge_description=charge.get("description", ""),
                billed_amount=billed_gst,
                expected_amount=expected_gst,
                tariff_ref=charge.get("tariff_ref", ""),
                message=f"GST mismatch: billed {billed_gst}, expected {expected_gst}"
            ))

        return issues, variance

    def _check_duplicates(self, charges: List[Dict]) -> List[ChargeIssue]:
        """Check for duplicate charges.

        Args:
            charges: List of charge items

        Returns:
            List of duplicate issues found
        """
        issues = []
        seen = {}

        for charge in charges:
            desc = charge.get("description", "")
            key = (desc, charge.get("tariff_ref", ""))

            if key in seen:
                issues.append(ChargeIssue(
                    flag_type=ChargeFlag.DUPLICATE_CHARGE,
                    charge_description=desc,
                    billed_amount=Decimal(str(charge.get("amount", 0))),
                    expected_amount=Decimal("0"),
                    tariff_ref=charge.get("tariff_ref", ""),
                    message=f"Duplicate charge found: {desc}"
                ))
            else:
                seen[key] = True

        return issues

    def _get_tariff_rate(self, tariff_ref: str, port: str = "") -> Decimal:
        """Get expected rate from tariff lookup.

        Args:
            tariff_ref: Tariff reference code
            port: Port/CFS location

        Returns:
            Expected rate or None if not found
        """
        # Try exact match first
        if tariff_ref in self.tariff_rates:
            rate = self.tariff_rates[tariff_ref]
            if isinstance(rate, dict):
                # Port-specific rate
                if port in rate:
                    return Decimal(str(rate[port]))
                return Decimal(str(rate.get("default", 0)))
            return Decimal(str(rate))

        return None
