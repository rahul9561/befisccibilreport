"""Generate a synthetic TrueLink JSON for a fictitious consumer.

Used to exercise pagination, long text and many-record handling.  All values
are random but deterministic for a given seed.

Usage:  python tools/make_synthetic.py [n_accounts] [n_enquiries] [out.json] [--seed N]
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MEMBERS = ["HDFC BANK", "ICICI BANK", "AXIS BANK", "KOTAK BANK", "BAJAJ FIN LTD", "TATA CAPITAL",
           "STATE BANK OF INDIA", "IDFC FIRST BANK", "YES BANK", "PUNJAB NATIONAL BANK",
           "ADITYA BIRLA FINANCE LIMITED - CONSUMER LENDING DIVISION (LONG NAME)"]
ACCOUNT_TYPES = ["01", "02", "05", "06", "07", "10", "13", "17", "50", "61"]
PAY_STATUSES = ["0", "0", "0", "0", "0", "15", "29", "30", "59", "90", "STD", "STD", "SMA", "SUB", "XXX"]


def enum(code: str, description: str = "") -> dict:
    return {"abbreviation": "", "description": description, "rank": "100000", "symbol": code}


def ymd(d: date) -> str:
    return d.isoformat() + "+05:30"


def first_of_month(d: date, back: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 - back, 12)
    return date(y, m + 1, 1)


def build(n_accounts: int = 40, n_enquiries: int = 60, seed: int = 7,
          name: str = "PRIYA RAMESH KULKARNI-DESHPANDE",
          report_date: date = date(2026, 5, 15)) -> dict:
    rng = random.Random(seed)
    tradelines = []
    for i in range(n_accounts):
        opened = report_date - timedelta(days=rng.randint(60, 4000))
        months = rng.randint(1, 36)
        newest = first_of_month(report_date, rng.randint(0, 6))
        hist = {str(k + 1): {"date": ymd(first_of_month(newest, k)), "status": rng.choice(PAY_STATUSES)}
                for k in range(months)}
        closed = rng.random() < 0.4
        overdue = rng.choice(["0", "0", "0", "-1", str(rng.randint(100, 90000))])
        tradelines.append({
            "accountTypeSymbol": rng.choice(ACCOUNT_TYPES),
            "Tradeline": {
                "creditorName": rng.choice(MEMBERS),
                "accountNumber": f"SYN{seed:02d}{i:04d}{rng.randint(10**9, 10**10 - 1)}"
                                 + ("XXXXXXXXXXXXXXXX" if i % 13 == 0 else ""),
                "AccountDesignator": enum(rng.choice(["1", "1", "1", "2", "3", "4"])),
                "dateOpened": ymd(opened),
                "dateReported": ymd(newest + timedelta(days=27)),
                "dateClosed": ymd(newest + timedelta(days=10)) if closed else "",
                "highBalance": str(rng.randint(5000, 5_000_000)),
                "currentBalance": "0" if closed else str(rng.randint(-500, 4_000_000)),
                "writtenOffPrincipal": str(rng.randint(1000, 90000)) if i % 9 == 0 else "-1",
                "writtenOffAmtTotal": str(rng.randint(1000, 90000)) if i % 9 == 0 else "-1",
                "settlementAmount": str(rng.randint(1000, 90000)) if i % 11 == 0 else "-1",
                "CreditFacilityStatus": enum("02" if i % 9 == 0 else ("03" if i % 11 == 0 else "")),
                "GrantedTrade": {
                    "amountPastDue": overdue,
                    "interestRate": f"{rng.uniform(7, 36):.2f}" if rng.random() < 0.7 else "-1.00",
                    "dateLastPayment": ymd(newest + timedelta(days=5)),
                    "CreditLimit": str(rng.randint(10000, 500000)) if rng.random() < 0.2 else "-1",
                    "actualPaymentAmount": str(rng.randint(500, 60000)) if rng.random() < 0.6 else "-1",
                    "EMIAmount": str(rng.randint(500, 60000)) if rng.random() < 0.8 else "-1",
                    "termMonths": str(rng.choice([12, 24, 36, 60, 84, 240])) if rng.random() < 0.8 else "-1",
                    "collateral": str(rng.randint(100000, 9000000)) if rng.random() < 0.2 else "-1",
                    "CashLimit": "-1",
                    "CollateralType": enum(rng.choice(["00", "01", "02", "04", ""])),
                    "PaymentFrequency": enum(rng.choice(["03", "03", "01", ""])),
                    "PayStatusHistory": {"MonthlyPayStatus": hist, "startDate": ymd(newest),
                                         "endDate": ymd(first_of_month(newest, months - 1))},
                },
            },
        })
    enquiries = []
    for i in range(n_enquiries):
        d = report_date - timedelta(days=rng.randint(0, 1200))
        enquiries.append({"Inquiry": {"subscriberName": rng.choice(MEMBERS), "inquiryDate": ymd(d),
                                      "inquiryType": rng.choice(ACCOUNT_TYPES + ["00"]),
                                      "amount": str(rng.randint(1, 5_000_000))}})
    addresses = [{
        "CreditAddress": {"StreetAddress": street, "City": "", "Region": "27", "PostalCode": "411038"},
        "Dwelling": enum(cat), "Ownership": enum(own), "dateReported": ymd(report_date - timedelta(days=d)),
    } for street, cat, own, d in [
        ("FLAT NO 1204, TOWER B, SUNSHINE HEIGHTS CO-OPERATIVE HOUSING SOCIETY, NEAR KOTHRUD DEPOT, "
         "PAUD ROAD, KOTHRUD, PUNE, MAHARASHTRA - VERY LONG ADDRESS LINE THAT MUST WRAP CLEANLY", "02", "01", 30),
        ("OFFICE 5, BUSINESS BAY, AIRPORT ROAD, YERWADA PUNE", "03", "02", 400),
        ("AT POST WAKAD, TAL MULSHI, DIST PUNE", "01", "", 900),
    ]]
    report = {
        "Borrower": {
            "BorrowerName": {"Name": {"Forename": name}},
            "Birth": {"date": "1988-02-29+05:30"},
            "Gender": "Female",
            "CreditScore": {"riskScore": "742", "scoreName": "CIBILTransUnionScore3", "CreditScoreFactor": [
                {"FactorText": ["Too many enquiries in the recent past"], "Factor": enum("")},
                {"FactorText": ["High utilisation of revolving credit lines relative to limits"], "Factor": enum("")},
                {"FactorText": ["Recent delinquency on an instalment account"], "Factor": enum("")},
            ]},
            "IdentifierPartition": {"Identifier": [
                {"ID": {"Id": "ABCDE1234F", "IdentifierName": "TaxId"}},
                {"ID": {"Id": "XXXXXXXX9012", "IdentifierName": "UID"}},
                {"ID": {"Id": "P1234567", "IdentifierName": "PassportId", "IssueDate": "2019-06-01",
                        "ExpirationDate": "2029-05-31"}},
                {"ID": {"Id": "MH1220110012345", "IdentifierName": "DriverLicense"}},
            ]},
            "BorrowerTelephone": [
                {"PhoneNumber": {"Number": "9800000001"}, "PhoneType": enum("01")},
                {"PhoneNumber": {"Number": "02026001234", "Extension": "221"}, "PhoneType": enum("03")},
                {"PhoneNumber": {"Number": "02025550000"}, "PhoneType": enum("02")},
            ],
            "EmailAddress": [{"Email": "priya.k@example.com"}, {"Email": "pkulkarni.work@example.org"}],
            "BorrowerAddress": addresses,
            "Employer": [{"account": "05", "name": "EXAMPLE SOFTWARE SERVICES PVT LTD",
                          "dateReported": "2026-03-31+05:30", "OccupationCode": enum("01"),
                          "income": "185000", "NetGrossIndicator": "N", "IncomeFreqIndicator": "M"}],
        },
        "ReferenceKey": "99000012345",
        "TradeLinePartition": tradelines,
        "InquiryPartition": enquiries,
    }
    return {"success": True, "raw_response": {"result": {"cibilData": {"GetCustomerAssetsResponse": {
        "GetCustomerAssetsSuccess": {"Asset": {"CreationDate": f"{report_date.isoformat()}T16:45:10+05:30",
                                               "TrueLinkCreditReport": report}}}}}}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("n_accounts", nargs="?", type=int, default=40)
    ap.add_argument("n_enquiries", nargs="?", type=int, default=60)
    ap.add_argument("out", nargs="?", default=str(ROOT / "tests" / "fixtures" / "synthetic_many_accounts.json"))
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build(a.n_accounts, a.n_enquiries, a.seed), indent=2), encoding="utf-8")
    print(f"wrote {out}: {a.n_accounts} accounts, {a.n_enquiries} enquiries")


if __name__ == "__main__":
    main()
