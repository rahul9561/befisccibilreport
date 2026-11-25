"""Data mapping: TrueLink JSON -> report model."""

from datetime import date
from decimal import Decimal

from befisc_reportforge import parse_report


def test_sample_header_and_consumer(sample_doc):
    r = parse_report(sample_doc)
    assert r.consumer.name == "ANAND VARDHAN GOYAL S/O RAM GOPAL"
    assert r.consumer.date_of_birth == "1995-10-04"
    assert r.consumer.gender == "male"
    assert r.header.control_number == "12060011928"
    assert r.header.report_date == date(2026, 11, 24)
    assert r.scores[0].value == "837"
    assert r.scores[0].name == "CIBILTRANSUNIONSCORE3"


def test_sample_contacts(sample_doc):
    r = parse_report(sample_doc)
    assert [i.label for i in r.identifications][0] == "INCOME TAX ID NUMBER (PAN)"  # PAN listed first
    assert {i.number for i in r.identifications} == {"CAZPG3241C", "3806889333", "60022246625681"}
    assert [(t.type, t.number) for t in r.telephones] == [("Mobile Phone", "9217010023"),
                                                         ("Office Phone", "9217010023")]
    assert r.emails == ["ANANDVARDHAN001@GMAIL.COM"]
    assert len(r.addresses) == 4
    assert r.addresses[0].category == "Residence Address" and r.addresses[0].residence_code == "Owned"
    assert r.addresses[1].text == "SUNAM,PUNJAB, ,99, 999998"
    assert r.employment[0].occupation == "Self Employed Professional"


def test_sample_account_mapping(sample_doc):
    r = parse_report(sample_doc)
    assert len(r.accounts) == 10
    pnb = r.accounts[-1]
    assert (pnb.member_name, pnb.account_type, pnb.ownership) == ("PNB", "Housing Loan", "Joint")
    assert pnb.account_closed == "NA"                       # open account
    assert pnb.collateral_type == "Property" and pnb.payment_frequency == "Monthly"
    assert pnb.emi == "43945" and pnb.repayment_tenure == "140"
    assert pnb.credit_limit == "-1"                         # reference prints -1 for this field
    assert pnb.cash_limit == "" and pnb.written_off_total == ""   # ...and blanks these
    assert pnb.suit_filed == "-"
    # Payment-history window: START is the oldest month, END the newest
    assert (pnb.pmt_hist_start, pnb.pmt_hist_end) == ("2023-11-01", "2026-10-01")
    assert len(pnb.payment_history) == 36
    assert pnb.payment_history[0].month == "10-26" and pnb.payment_history[-1].month == "11-23"
    assert pnb.payment_history[0].status == "000"


def test_raw_bureau_enquiries_are_complete(sample_doc):
    r = parse_report(sample_doc)
    assert len(r.enquiries) == 26                           # TrueLink only has 5
    assert [e.date for e in r.enquiries] == sorted((e.date for e in r.enquiries), reverse=True)
    r2 = parse_report(sample_doc, use_raw_bureau_data=False)
    assert len(r2.enquiries) == 5


def test_reference_fixture_summary_matches_reference_pdf(reference_doc):
    """Values printed in sample/report.pdf's SUMMARY section."""
    r = parse_report(reference_doc)
    a, e = r.account_summary, r.enquiry_summary
    assert (a.total, a.overdue_count, a.zero_balance_count) == (10, 2, 7)
    assert a.high_credit_total == Decimal(5278275)
    assert a.current_balance_total == Decimal(1258195)
    # Reference prints 227546 because it summed four "-1" sentinels; we exclude them.
    assert a.overdue_total == Decimal(227550)
    assert (a.most_recent_opened, a.oldest_opened) == (date(2025, 3, 27), date(2014, 3, 12))
    assert (e.total, e.past_30_days, e.past_12_months, e.past_24_months) == (9, 1, 5, 8)
    assert e.most_recent == date(2026, 11, 16)


def test_reference_fixture_details(reference_doc):
    r = parse_report(reference_doc)
    assert r.header.report_time.strftime("%I:%M %p") == "11:30 PM"
    first = r.accounts[0]
    assert first.ownership == "Guarantor" and first.credit_facility_status == "Written-off"
    assert [p.status for p in first.payment_history] == ["900", "900", "900"]
    hero = r.accounts[-1]
    assert hero.account_type == "Two wheeler Loan"
    assert [i.label for i in r.identifications][:2] == ["INCOME TAX ID NUMBER (PAN)", "UNIVERSAL ID NUMBER (UID)"]
