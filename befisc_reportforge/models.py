"""Typed, display-ready report model produced by the parser.

String fields hold exactly what is printed (already translated, formatted and
blank where the reference leaves them blank).  Fields needed for calculations
keep their parsed numeric/date form alongside.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class ReportHeader:
    consumer_name: str = ""
    member_id: str = ""
    member_reference: str = ""
    report_date: Optional[date] = None
    report_time: Optional[datetime] = None
    control_number: str = ""


@dataclass
class Consumer:
    name: str = ""
    date_of_birth: str = ""
    gender: str = ""


@dataclass
class Score:
    name: str = ""
    value: str = ""
    factors: list[str] = field(default_factory=list)


@dataclass
class Identification:
    label: str
    number: str
    issue_date: str = ""
    expiration_date: str = ""


@dataclass
class Telephone:
    type: str
    number: str
    extension: str = ""


@dataclass
class Address:
    text: str
    category: str = ""
    residence_code: str = ""
    date_reported: str = ""


@dataclass
class Employment:
    account_type: str = ""
    employer_name: str = ""
    date_reported: str = ""
    occupation: str = ""
    income: str = ""
    net_gross: str = ""
    monthly_annual: str = ""

    def is_empty(self) -> bool:
        return not any(vars(self).values())


@dataclass
class PaymentStatus:
    status: str   # e.g. "000", "029", "STD"
    month: str    # "MM-YY"


@dataclass
class Account:
    # ACCOUNT column
    member_name: str = ""
    account_number: str = ""
    account_type: str = ""
    ownership: str = ""
    amount_overdue: str = ""
    interest_rate: str = ""
    # DATES column
    opened: str = ""
    reported: str = ""
    pmt_hist_start: str = ""
    pmt_hist_end: str = ""
    last_payment: str = ""
    collateral_type: str = ""
    # AMOUNTS column
    high_credit: str = ""
    credit_limit: str = ""
    actual_payment: str = ""
    current_balance: str = ""
    emi: str = ""
    payment_frequency: str = ""
    repayment_tenure: str = ""
    collateral_value: str = ""
    # STATUS column
    credit_facility_status: str = ""
    account_closed: str = ""
    written_off_principal: str = ""
    written_off_total: str = ""
    settlement_amount: str = ""
    suit_filed: str = ""
    cash_limit: str = ""
    # Payment history, newest first
    payment_history: list[PaymentStatus] = field(default_factory=list)
    # Parsed values for summary calculations (None = not reported)
    date_opened: Optional[date] = None
    high_credit_value: Optional[Decimal] = None
    current_balance_value: Optional[Decimal] = None
    overdue_value: Optional[Decimal] = None


@dataclass
class Enquiry:
    member: str
    date: str
    purpose: str
    amount: str
    date_value: Optional[date] = None


@dataclass
class AccountSummary:
    total: int = 0
    overdue_count: int = 0
    zero_balance_count: int = 0
    high_credit_total: Decimal = Decimal(0)
    current_balance_total: Decimal = Decimal(0)
    overdue_total: Decimal = Decimal(0)
    most_recent_opened: Optional[date] = None
    oldest_opened: Optional[date] = None


@dataclass
class EnquirySummary:
    total: int = 0
    past_30_days: int = 0
    past_12_months: int = 0
    past_24_months: int = 0
    most_recent: Optional[date] = None


@dataclass
class CreditReport:
    header: ReportHeader = field(default_factory=ReportHeader)
    consumer: Consumer = field(default_factory=Consumer)
    scores: list[Score] = field(default_factory=list)
    identifications: list[Identification] = field(default_factory=list)
    telephones: list[Telephone] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    addresses: list[Address] = field(default_factory=list)
    employment: list[Employment] = field(default_factory=list)
    accounts: list[Account] = field(default_factory=list)
    enquiries: list[Enquiry] = field(default_factory=list)
    account_summary: AccountSummary = field(default_factory=AccountSummary)
    enquiry_summary: EnquirySummary = field(default_factory=EnquirySummary)
    warnings: list[str] = field(default_factory=list)
