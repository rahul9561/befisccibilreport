"""Map TransUnion CIBIL TrueLink JSON to the :mod:`models` report.

Data sources, in order of precedence:

1. ``TrueLinkCreditReport`` - the structured report (primary source).
2. ``Sources.Source.OriginalData`` - base64 of the raw TUEF bureau response.
   Used to fill fields the TrueLink structure omits (credit-facility status,
   suit-filed status, residence code, full enquiry list, raw payment history).

All access is null-safe: absent sections produce empty lists / blank strings,
never exceptions.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from .calculations import summarise_accounts, summarise_enquiries
from .data import codes
from .models import (
    Account, Address, Consumer, CreditReport, Employment, Enquiry, Identification,
    PaymentStatus, ReportHeader, Score, Telephone,
)
from .utils.dates import fmt_date, fmt_month, parse_date, parse_datetime
from .utils.values import (
    SENTINEL, as_list, described, dig, first_nonempty, is_reported, symbol, text, to_number, unique,
)
from .validators import validate_document

log = logging.getLogger(__name__)

MAX_PAYMENT_HISTORY = 36


# --------------------------------------------------------------------------- helpers

def _raw_or_blank(value: Any) -> str:
    """Show the value as reported, but blank for the -1 sentinel."""
    return text(value) if is_reported(value) else ""


def _raw(value: Any) -> str:
    """Show the value exactly as reported (the reference prints -1 for these)."""
    return text(value)


def _fmt_rate(value: Any) -> str:
    num = to_number(value)
    if num is None:
        return text(value)
    return f"{num:.2f}"


def _number_or_none(value: Any) -> Optional[Decimal]:
    num = to_number(value)
    return None if num is None or num == SENTINEL else num


def _decode_original_data(report: dict) -> dict:
    """Decode the raw TUEF payload; return the first ``subject`` or ``{}``."""
    blobs = [dig(s, "OriginalData") for s in as_list(dig(report, "Sources", "Source"))]
    for blob in blobs:
        if not isinstance(blob, str) or not blob.strip():
            continue
        try:
            raw = json.loads(base64.b64decode(blob, validate=False).decode("utf-8"))
        except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
            log.warning("OriginalData could not be decoded (%s); continuing without it", exc)
            continue
        resp = raw.get("ICRS_SubjectInquiryByTUEF_Response") if isinstance(raw, dict) else None
        subject = dig(resp, "subject", 0)
        if isinstance(subject, dict):
            return {"subject": subject, "response": resp}
    return {}


def _pick(node: Any, *keys: str) -> Any:
    """First present (non-empty) key of ``node`` among ``keys``."""
    if not isinstance(node, dict):
        return None
    for key in keys:
        val = node.get(key)
        if val not in (None, "", {}, []):
            return val
    return None


# --------------------------------------------------------------------------- parser

class CibilParser:
    """Parse one TrueLink credit report into a :class:`CreditReport`."""

    def __init__(self, use_raw_bureau_data: bool = True) -> None:
        self.use_raw_bureau_data = use_raw_bureau_data

    def parse(self, document: Any) -> CreditReport:
        result = validate_document(document)
        report = result.report
        borrower = report.get("Borrower") or {}
        raw = _decode_original_data(report) if self.use_raw_bureau_data else {}
        subject = raw.get("subject", {})

        out = CreditReport(warnings=list(result.warnings))
        out.header = self._header(document, report, borrower, raw)
        out.consumer = self._consumer(borrower, subject)
        out.header.consumer_name = out.consumer.name
        out.scores = self._scores(borrower)
        out.identifications = self._identifications(borrower, subject)
        out.telephones = self._telephones(borrower, subject)
        out.emails = self._emails(borrower, subject)
        out.addresses = self._addresses(borrower, subject)
        out.employment = self._employment(borrower, subject)
        out.accounts = self._accounts(report, subject)
        out.enquiries = self._enquiries(report, subject)
        out.account_summary = summarise_accounts(out.accounts)
        out.enquiry_summary = summarise_enquiries(out.enquiries, out.header.report_date)
        for w in out.warnings:
            log.warning("input warning: %s", w)
        return out

    # ---- header -------------------------------------------------------------
    def _header(self, document: Any, report: dict, borrower: dict, raw: dict) -> ReportHeader:
        asset = None
        if isinstance(document, dict):
            from .validators import find_key

            found = find_key(document, "Asset")
            asset = found[0] if found and isinstance(found[0], dict) else None

        stamp: Optional[datetime] = None
        for candidate in (
            dig(asset, "CreationDate"),
            dig(report, "Sources", "Source", "InquiryDate"),
            dig(raw, "response", "timestamp"),
            dig(borrower, "Birth", "Source", "InquiryDate"),
            dig(document, "raw_response", "datetime"),
        ):
            stamp = parse_datetime(candidate) if candidate else None
            if stamp:
                break
        if stamp is None and dig(raw, "response", "timestamp"):
            # TUEF timestamps look like 2026-11-24T11:24:36+0530
            ts = str(dig(raw, "response", "timestamp"))
            try:
                stamp = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                stamp = None

        resp = raw.get("response") or {}
        return ReportHeader(
            member_id=first_nonempty(_pick(resp, "memberId", "memberCode"), dig(resp, "header", "memberId")),
            member_reference=first_nonempty(
                _pick(resp, "memberReferenceNumber", "memberRefNo"),
                dig(resp, "header", "memberReferenceNumber"),
            ),
            report_date=stamp.date() if stamp else None,
            report_time=stamp,
            control_number=first_nonempty(report.get("ReferenceKey"), resp.get("ecn")),
        )

    # ---- consumer -----------------------------------------------------------
    def _consumer(self, borrower: dict, subject: dict) -> Consumer:
        name_node = dig(as_list(borrower.get("BorrowerName")), 0, "Name") or {}
        parts = [text(name_node.get(k)) for k in ("Forename", "MiddleName", "Surname")] if isinstance(name_node, dict) else []
        name = " ".join(p for p in parts if p)
        if not name:
            sn = subject.get("name") or {}
            name = " ".join(text(sn.get(f"name{i}")) for i in range(1, 6) if text(sn.get(f"name{i}")))

        birth = borrower.get("Birth") or {}
        dob = fmt_date(birth.get("date"))
        if not dob:
            bd = birth.get("BirthDate") or {}
            try:
                dob = datetime(int(bd["year"]), int(bd["month"]), int(bd["day"])).date().isoformat()
            except (KeyError, TypeError, ValueError):
                dob = fmt_date(dig(subject, "name", "dob"))

        gender = text(borrower.get("Gender")).lower()
        if not gender:
            gender = codes.lookup(codes.GENDER, text(dig(subject, "name", "gender")))
        return Consumer(name=name, date_of_birth=dob, gender=gender)

    # ---- scores -------------------------------------------------------------
    def _scores(self, borrower: dict) -> list[Score]:
        scores = []
        for node in as_list(borrower.get("CreditScore")):
            if not isinstance(node, dict):
                continue
            factors = []
            for f in as_list(node.get("CreditScoreFactor")):
                texts = as_list(dig(f, "FactorText"))
                label = text(texts[0]) if texts else described(dig(f, "Factor"))
                factors.append(label.upper())
            factors = list(unique(f for f in factors if f))
            # Drop "no valid factors" placeholders only when real factors exist.
            real = [f for f in factors if f not in codes.NO_FACTOR_TEXTS]
            scores.append(Score(
                name=first_nonempty(node.get("scoreName"), symbol(node.get("CreditScoreModel"))).upper(),
                value=text(node.get("riskScore")),
                factors=real or factors,
            ))
        return scores

    # ---- identifications ----------------------------------------------------
    def _identifications(self, borrower: dict, subject: dict) -> list[Identification]:
        items: list[Identification] = []
        for ident in as_list(dig(borrower, "IdentifierPartition", "Identifier")):
            node = ident.get("ID") if isinstance(ident, dict) else None
            if not isinstance(node, dict):
                continue
            kind = text(node.get("IdentifierName"))
            number = text(node.get("Id"))
            if not (kind or number):
                continue
            items.append(Identification(
                label=codes.ID_LABELS.get(kind, kind),
                number=number,
                issue_date=fmt_date(_pick(node, "IssueDate", "issueDate")),
                expiration_date=fmt_date(_pick(node, "ExpirationDate", "expirationDate")),
            ))
        if not items:
            for node in as_list(subject.get("id")):
                kind = codes.lookup(codes.ID_TYPE_CODES, text(node.get("idType")))
                items.append(Identification(
                    label=codes.ID_LABELS.get(kind, kind), number=text(node.get("idNumber")),
                    issue_date=fmt_date(node.get("issueDate")),
                    expiration_date=fmt_date(node.get("expirationDate")),
                ))
        prio = {label: i for i, label in enumerate(codes.ID_PRIORITY)}
        items.sort(key=lambda it: prio.get(it.label, len(prio)))  # stable sort keeps input order
        return items

    # ---- contacts -----------------------------------------------------------
    def _telephones(self, borrower: dict, subject: dict) -> list[Telephone]:
        out = []
        for t in as_list(borrower.get("BorrowerTelephone")):
            if not isinstance(t, dict):
                continue
            number = text(dig(t, "PhoneNumber", "Number"))
            if not number:
                continue
            out.append(Telephone(
                type=described(t.get("PhoneType"), codes.TELEPHONE_TYPE),
                number=number,
                extension=text(dig(t, "PhoneNumber", "Extension")),
            ))
        if not out:
            for t in as_list(subject.get("telephone")):
                if text(t.get("telephoneNumber")):
                    out.append(Telephone(
                        type=codes.lookup(codes.TELEPHONE_TYPE, text(t.get("telephoneType"))),
                        number=text(t.get("telephoneNumber")),
                        extension=text(t.get("telephoneExtension")),
                    ))
        return out

    def _emails(self, borrower: dict, subject: dict) -> list[str]:
        emails = [text(dig(e, "Email")) for e in as_list(borrower.get("EmailAddress"))]
        if not any(emails):
            emails = [text(e.get("emailID")) for e in as_list(subject.get("email")) if isinstance(e, dict)]
        return list(unique(e for e in emails if e))

    # ---- addresses ----------------------------------------------------------
    def _addresses(self, borrower: dict, subject: dict) -> list[Address]:
        raw_by_serial = {text(a.get("serialNumber")): a for a in as_list(subject.get("address")) if isinstance(a, dict)}
        out = []
        for a in as_list(borrower.get("BorrowerAddress")):
            if not isinstance(a, dict):
                continue
            ca = a.get("CreditAddress") or {}
            street = text(ca.get("StreetAddress"))
            if not street and not text(ca.get("PostalCode")):
                continue
            raw = raw_by_serial.get(text(ca.get("SerialNumber")), {})
            category_code = first_nonempty(symbol(a.get("Dwelling")), raw.get("addressCategory"))
            residence_code = first_nonempty(symbol(a.get("Ownership")), raw.get("residenceCode"))
            category = text(dig(a, "Dwelling", "description")) or codes.lookup(codes.ADDRESS_CATEGORY, category_code)
            residence = text(dig(a, "Ownership", "description")) or codes.lookup(codes.RESIDENCE_CODE, residence_code)
            out.append(Address(
                text=f"{street}, {text(ca.get('City'))},{text(ca.get('Region'))}, {text(ca.get('PostalCode'))}",
                category=category,
                residence_code=residence,
                date_reported=fmt_date(a.get("dateReported")),
            ))
        if not out:
            for raw in raw_by_serial.values():
                street = " ".join(text(raw.get(f"line{i}")) for i in range(1, 6) if text(raw.get(f"line{i}")))
                out.append(Address(
                    text=f"{street}, ,{text(raw.get('stateCode'))}, {text(raw.get('pinCode'))}",
                    category=codes.lookup(codes.ADDRESS_CATEGORY, text(raw.get("addressCategory"))),
                    residence_code=codes.lookup(codes.RESIDENCE_CODE, text(raw.get("residenceCode"))),
                    date_reported=fmt_date(raw.get("reportedDate")),
                ))
        return out

    # ---- employment ---------------------------------------------------------
    def _employment(self, borrower: dict, subject: dict) -> list[Employment]:
        out = []
        for e in as_list(borrower.get("Employer")):
            if not isinstance(e, dict):
                continue
            income = _pick(e, "income", "Income", "IncomeAmount")
            emp = Employment(
                account_type=codes.lookup(codes.ACCOUNT_TYPE, text(e.get("account"))),
                employer_name=text(e.get("name")),
                date_reported=fmt_date(e.get("dateReported")),
                occupation=described(e.get("OccupationCode"), codes.OCCUPATION),
                income=_raw_or_blank(income) if income is not None else "",
                net_gross=codes.lookup(codes.NET_GROSS_INDICATOR, text(e.get("NetGrossIndicator"))),
                monthly_annual=codes.lookup(codes.MONTHLY_ANNUAL_INDICATOR, text(e.get("IncomeFreqIndicator"))),
            )
            if not emp.is_empty():
                out.append(emp)
        if not out:
            e = subject.get("employment")
            if isinstance(e, dict) and e:
                emp = Employment(
                    account_type=codes.lookup(codes.ACCOUNT_TYPE, text(e.get("accountType"))),
                    date_reported=fmt_date(e.get("reportedDate")),
                    occupation=codes.lookup(codes.OCCUPATION, text(e.get("occupationCode"))),
                    income=_raw_or_blank(e.get("income")),
                    net_gross=codes.lookup(codes.NET_GROSS_INDICATOR, text(e.get("netGrossIndicator"))),
                    monthly_annual=codes.lookup(codes.MONTHLY_ANNUAL_INDICATOR, text(e.get("monthlyAnnualIndicator"))),
                )
                if not emp.is_empty():
                    out.append(emp)
        return out

    # ---- accounts -----------------------------------------------------------
    def _accounts(self, report: dict, subject: dict) -> list[Account]:
        raw_accounts = [a for a in as_list(subject.get("account")) if isinstance(a, dict)]
        by_serial = {text(a.get("serialNumber")): a for a in raw_accounts}
        by_number = {(text(a.get("accountNumber")), text(a.get("memberShortName"))): a for a in raw_accounts}

        out = []
        partitions = as_list(report.get("TradeLinePartition"))
        for part in partitions:
            tl = dig(part, "Tradeline")
            for t in as_list(tl):
                if not isinstance(t, dict):
                    continue
                g = t.get("GrantedTrade") or {}
                if isinstance(g, list):
                    g = g[0] if g else {}
                raw = by_serial.get(text(g.get("serialNumber"))) or by_number.get(
                    (text(t.get("accountNumber")), text(t.get("creditorName")))
                ) or {}
                out.append(self._account(part, t, g, raw))
        if not out and raw_accounts:
            out = [self._account({}, {}, {}, raw) for raw in raw_accounts]
        return out

    def _account(self, part: dict, t: dict, g: dict, raw: dict) -> Account:
        type_code = first_nonempty(part.get("accountTypeSymbol"), symbol(g.get("AccountType")), raw.get("accountType"))
        type_desc = first_nonempty(part.get("accountTypeDescription"), dig(g, "AccountType", "description"))

        def pick(tl_value: Any, raw_key: str) -> Any:
            return tl_value if text(tl_value) else raw.get(raw_key)

        overdue = pick(g.get("amountPastDue"), "amountOverdue")
        high = pick(t.get("highBalance"), "highCreditAmount")
        balance = pick(t.get("currentBalance"), "currentBalance")

        facility = first_nonempty(
            dig(t, "CreditFacilityStatus", "description"),
            codes.lookup(codes.CREDIT_FACILITY_STATUS, first_nonempty(
                symbol(t.get("CreditFacilityStatus")),
                raw.get("creditFacilityStatus"), raw.get("writtenOffAndSettledStatus"),
                raw.get("writtenOffAndSettled"),
            )),
        )
        suit = codes.lookup(codes.SUIT_FILED, first_nonempty(
            symbol(t.get("SuitFiledWilfulDefault")), raw.get("suitFiledWilfulDefault"),
            raw.get("suitFiled"), raw.get("suitFiledStatus"),
        ))
        if suit in ("", "No Suit Filed"):
            suit = "-"

        history = self._payment_history(g, raw)
        hist_start = pick(dig(g, "PayStatusHistory", "startDate"), "paymentHistStartDate")
        hist_end = pick(dig(g, "PayStatusHistory", "endDate"), "paymentHistEndDate")
        # The reference shows START as the oldest month and END as the newest.
        d_start, d_end = parse_date(hist_start), parse_date(hist_end)
        if d_start and d_end and d_start > d_end:
            d_start, d_end = d_end, d_start

        closed = fmt_date(pick(t.get("dateClosed"), "dateClosed"))
        return Account(
            member_name=first_nonempty(t.get("creditorName"), raw.get("memberShortName")),
            account_number=first_nonempty(t.get("accountNumber"), raw.get("accountNumber")),
            account_type=type_desc or codes.lookup(codes.ACCOUNT_TYPE, type_code),
            ownership=described(t.get("AccountDesignator"), codes.OWNERSHIP)
            or codes.lookup(codes.OWNERSHIP, text(raw.get("ownershipIndicator"))),
            amount_overdue=_raw(overdue),
            interest_rate=_fmt_rate(pick(g.get("interestRate"), "rateOfInterest")),
            opened=fmt_date(pick(t.get("dateOpened"), "dateOpened")),
            reported=fmt_date(pick(t.get("dateReported"), "reportedDate")),
            pmt_hist_start=d_start.isoformat() if d_start else "",
            pmt_hist_end=d_end.isoformat() if d_end else "",
            last_payment=fmt_date(pick(g.get("dateLastPayment"), "dateOfLastPayment")),
            collateral_type=described(g.get("CollateralType"), codes.COLLATERAL_TYPE)
            or codes.lookup(codes.COLLATERAL_TYPE, text(raw.get("typeOfCollateral"))),
            high_credit=_raw(high),
            credit_limit=_raw(pick(g.get("CreditLimit"), "creditLimit")),
            actual_payment=_raw(pick(g.get("actualPaymentAmount"), "actualPaymentAmount")),
            current_balance=_raw(balance),
            emi=_raw_or_blank(pick(g.get("EMIAmount"), "EMIAmount")),
            payment_frequency=described(g.get("PaymentFrequency"), codes.PAYMENT_FREQUENCY)
            or codes.lookup(codes.PAYMENT_FREQUENCY, text(raw.get("paymentFrequency"))),
            repayment_tenure=_raw_or_blank(pick(g.get("termMonths"), "repaymentTenure")),
            collateral_value=_raw_or_blank(pick(g.get("collateral"), "valueOfCollateral")),
            credit_facility_status=facility,
            account_closed=closed or "NA",
            written_off_principal=_raw_or_blank(pick(t.get("writtenOffPrincipal"), "writtenOffAmtPrincipal")),
            written_off_total=_raw_or_blank(pick(t.get("writtenOffAmtTotal"), "writtenOffAmtTotal")),
            settlement_amount=_raw_or_blank(pick(t.get("settlementAmount"), "settlementAmount")),
            suit_filed=suit,
            cash_limit=_raw_or_blank(pick(g.get("CashLimit"), "cashLimit")),
            payment_history=history,
            date_opened=parse_date(pick(t.get("dateOpened"), "dateOpened")),
            high_credit_value=_number_or_none(high),
            current_balance_value=_number_or_none(balance),
            overdue_value=_number_or_none(overdue),
        )

    @staticmethod
    def _status(value: Any) -> str:
        s = text(value).upper()
        if not s:
            return "XXX"
        if s.lstrip("-").isdigit():
            n = int(s)
            return "XXX" if n < 0 else str(n).zfill(3)
        return s

    def _payment_history(self, g: dict, raw: dict) -> list[PaymentStatus]:
        monthly = dig(g, "PayStatusHistory", "MonthlyPayStatus")
        entries: list[tuple[Any, Any]] = []
        if isinstance(monthly, dict):
            def order(k: str) -> tuple[int, str]:
                return (int(k), k) if str(k).isdigit() else (10**6, str(k))
            entries = [(monthly[k].get("status"), monthly[k].get("date"))
                       for k in sorted(monthly, key=order) if isinstance(monthly[k], dict)]
        elif isinstance(monthly, list):
            entries = [(m.get("status"), m.get("date")) for m in monthly if isinstance(m, dict)]

        if not entries and raw.get("paymentHistory") is not None:
            from .utils.dates import months_before

            start = parse_date(raw.get("paymentHistStartDate"))
            values = as_list(raw.get("paymentHistory"))
            entries = [(v, months_before(start, i) if start else None) for i, v in enumerate(values)]

        history = [PaymentStatus(status=self._status(s), month=fmt_month(d)) for s, d in entries]
        # Newest first, as printed left-to-right in the reference.
        dated = [(parse_date(d), i) for i, (_, d) in enumerate(entries)]
        if all(d for d, _ in dated) and len(dated) > 1 and dated[0][0] < dated[-1][0]:
            history.reverse()
        return history[:MAX_PAYMENT_HISTORY]

    # ---- enquiries ----------------------------------------------------------
    def _enquiries(self, report: dict, subject: dict) -> list[Enquiry]:
        truelink = []
        for part in as_list(report.get("InquiryPartition")):
            for q in as_list(dig(part, "Inquiry")):
                if not isinstance(q, dict):
                    continue
                truelink.append(Enquiry(
                    member=text(q.get("subscriberName")),
                    date=fmt_date(q.get("inquiryDate")),
                    purpose=text(q.get("description")) or codes.lookup(codes.ENQUIRY_PURPOSE, text(q.get("inquiryType"))),
                    amount=_raw_or_blank(q.get("amount")),
                    date_value=parse_date(q.get("inquiryDate")),
                ))
        raw = []
        for q in as_list(subject.get("inquiry")):
            if not isinstance(q, dict):
                continue
            if dig(q, "inquiryRules", "partOfCIR") is False:
                continue
            raw.append(Enquiry(
                member=text(q.get("memberShortName")),
                date=fmt_date(q.get("dateOfInquiry")),
                purpose=codes.lookup(codes.ENQUIRY_PURPOSE, text(q.get("inquiryPurpose"))),
                amount=_raw_or_blank(q.get("inquiryAmount")),
                date_value=parse_date(q.get("dateOfInquiry")),
            ))
        # TrueLink truncates the enquiry list; the raw bureau segment is complete.
        chosen = raw if len(raw) > len(truelink) else truelink
        chosen.sort(key=lambda e: e.date_value or datetime.min.date(), reverse=True)
        return chosen


def parse_report(document: Any, *, use_raw_bureau_data: bool = True) -> CreditReport:
    """Convenience wrapper around :class:`CibilParser`."""
    return CibilParser(use_raw_bureau_data=use_raw_bureau_data).parse(document)
