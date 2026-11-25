"""Rebuild a TrueLink-shaped JSON fixture from the reference PDF's text.

The supplied ``input/sample.json`` belongs to a different consumer than
``sample/report.pdf``, so the two cannot be compared visually.  This tool reads
the reference PDF and writes ``tests/fixtures/reference_consumer.json`` - the
same data the reference shows, in the input structure the engine consumes.
Generating a PDF from that fixture allows a like-for-like overlay comparison.

Usage:  python tools/build_reference_fixture.py [sample/report.pdf] [out.json]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from befisc_reportforge.data import codes  # noqa: E402


def rev(table: dict) -> dict:
    return {v.lower(): k for k, v in table.items()}


ACC = rev(codes.ACCOUNT_TYPE)
OWN = rev(codes.OWNERSHIP)
TEL = rev(codes.TELEPHONE_TYPE)
CAT = rev(codes.ADDRESS_CATEGORY)
COLL = rev(codes.COLLATERAL_TYPE)
FREQ = rev(codes.PAYMENT_FREQUENCY)
CFS = rev(codes.CREDIT_FACILITY_STATUS)
ID_NAME = {"income tax id number (pan)": "TaxId", "universal id number (uid)": "UID"}


def enum(code: str) -> dict:
    return {"abbreviation": "", "description": "", "rank": "100000", "symbol": code}


def val(v: str) -> str:
    return v if v else "-1"


def main(pdf_path: Path, out_path: Path) -> None:
    doc = pymupdf.open(pdf_path)
    lines = [ln.replace("​", "") for p in doc for ln in p.get_text().splitlines()]
    # Join the one field the reference wraps onto two lines.
    joined: list[str] = []
    for ln in lines:
        if joined and joined[-1].endswith(":") and re.fullmatch(r"[A-Z0-9]+", ln) and joined[-1] in (
            "WRITTEN-OFF AMOUNT(PRINCIPAL):", "ACCOUNT NUMBER:"):
            joined[-1] += " " + ln
        else:
            joined.append(ln)
    lines = joined

    def after(prefix: str, start: int = 0) -> str:
        for ln in lines[start:]:
            if ln.startswith(prefix):
                return ln[len(prefix):].strip()
        return ""

    idx = {ln: i for i, ln in reversed(list(enumerate(lines)))}

    # identifications
    ids, i = [], idx["EXPIRATION DATE"] + 1
    while lines[i] != "TELEPHONE(S):":
        name = ID_NAME.get(lines[i].lower(), lines[i])
        ids.append({"ID": {"Id": lines[i + 1], "IdentifierName": name}})
        i += 2
    phones, i = [], idx["TELEPHONE EXTENSION"] + 1
    while lines[i] != "EMAIL CONTACT(S):":
        phones.append({"PhoneNumber": {"Number": lines[i + 1]}, "PhoneType": enum(TEL[lines[i].lower()])})
        i += 2
    email = lines[idx["EMAIL ADDRESS"] + 1]

    addresses = []
    for j, ln in enumerate(lines):
        if ln.startswith("ADDRESS : "):
            m = re.match(r"^(.*), (.*),(\d*), (\d*)$", ln[len("ADDRESS : "):])
            cat = lines[j + 1].split(":", 1)[1].strip()
            addresses.append({
                "CreditAddress": {"StreetAddress": m.group(1), "City": m.group(2), "Region": m.group(3),
                                  "PostalCode": m.group(4)},
                "Dwelling": enum(CAT.get(cat.lower(), "")), "Ownership": enum(""),
                "dateReported": lines[j + 3].split(":", 1)[1].strip() + "+05:30",
            })

    emp_i = idx["INCOME INDICATOR"] + 1
    employer = {"account": ACC[lines[emp_i].lower()], "dateReported": lines[emp_i + 1] + "+05:30",
                "OccupationCode": enum("")}

    score = lines[idx["CIBILTRANSUNIONSCORE3"] + 1]
    factors, i = [], idx["CIBILTRANSUNIONSCORE3"] + 2
    while re.match(r"^\d+\. ", lines[i]):
        factors.append({"FactorText": [lines[i].split(". ", 1)[1]], "Factor": enum("")})
        i += 1

    # accounts
    tradelines = []
    starts = [k for k, ln in enumerate(lines) if ln == "ACCOUNT" and lines[k + 1] == "DATES"]
    for k in starts:
        end = next(j for j in range(k, len(lines)) if lines[j].startswith("DAYS PAST DUE"))
        f = {}
        for ln in lines[k + 4:end]:
            if ":" in ln:
                key, v = ln.split(":", 1)
                f[key.strip().upper()] = v.strip()
        hist, j = {}, end + 1
        n = 1
        while j + 1 < len(lines) and re.fullmatch(r"\d{2}-\d{2}", lines[j + 1]):
            mm, yy = lines[j + 1].split("-")
            hist[str(n)] = {"date": f"20{yy}-{mm}-01+05:30", "status": lines[j]}
            j += 2
            n += 1
        d = lambda key: (f.get(key) + "+05:30") if f.get(key) not in ("", None, "NA") else ""  # noqa: E731
        t = {
            "creditorName": f["MEMBER NAME"], "accountNumber": f["ACCOUNT NUMBER"],
            "AccountDesignator": enum(OWN[f["OWNERSHIP"].lower()]),
            "dateOpened": d("OPENED"), "dateReported": d("REPORTED AND CERTIFIED"),
            "dateClosed": d("ACCOUNT CLOSED"), "highBalance": f["HIGH CREDIT AMOUNT"],
            "currentBalance": f["CURRENT BALANCE"],
            "writtenOffPrincipal": val(f["WRITTEN-OFF AMOUNT(PRINCIPAL)"]),
            "writtenOffAmtTotal": val(f["WRITTEN-OFF AMOUNT(TOTAL)"]),
            "settlementAmount": val(f["SETTLEMENT AMOUNT"]),
            "CreditFacilityStatus": enum(CFS.get(f["CREDIT FACILITY STATUS"].lower(), "")),
            "GrantedTrade": {
                "amountPastDue": f["AMOUNT OVERDUE"], "interestRate": f["INTEREST RATE"],
                "dateLastPayment": d("LAST PAYMENT"), "CreditLimit": f["CREDIT LIMIT"],
                "actualPaymentAmount": f["ACTUAL PAYMENT AMOUNT"], "EMIAmount": val(f["EMI"]),
                "termMonths": val(f["REPAYMENT TENURE"]), "collateral": val(f["COLLATERAL VALUE"]),
                "CashLimit": val(f["CASH LIMIT"]),
                "CollateralType": enum(COLL.get(f["COLLATERAL TYPE"].lower(), "")),
                "PaymentFrequency": enum(FREQ.get(f["PAYMENT FREQUENCY"].lower(), "")),
                "PayStatusHistory": {"MonthlyPayStatus": hist,
                                     "startDate": d("PMT HIST END"), "endDate": d("PMT HIST START")},
            },
        }
        tradelines.append({"Tradeline": t, "accountTypeSymbol": ACC[f["TYPE"].lower()]})

    enquiries, i = [], idx["ENQUIRY AMOUNT"] + 1
    while not lines[i].startswith("All information"):
        member, date, purpose, amount = lines[i:i + 4]
        enquiries.append({"Inquiry": {"subscriberName": member, "inquiryDate": date + "+05:30",
                                      "inquiryType": ACC[purpose.lower()], "amount": amount}})
        i += 4

    date, time = after("DATE: "), after("TIME: ")
    hh, rest = time.split(":")
    mins, ampm = rest.split()
    hour = int(hh) % 12 + (12 if ampm == "PM" else 0)
    name = after("NAME: ")
    report = {
        "Borrower": {
            "BorrowerName": {"Name": {"Forename": name}},
            "Birth": {"date": after("DATE OF BIRTH: ") + "+05:30"},
            "Gender": after("GENDER: ").capitalize(),
            "CreditScore": {"riskScore": score, "scoreName": "CIBILTransUnionScore3",
                            "CreditScoreFactor": factors},
            "IdentifierPartition": {"Identifier": ids},
            "BorrowerTelephone": phones,
            "EmailAddress": {"Email": email},
            "BorrowerAddress": addresses,
            "Employer": employer,
        },
        "ReferenceKey": after("CONTROL NUMBER: "),
        "TradeLinePartition": tradelines,
        "InquiryPartition": enquiries,
    }
    document = {"success": True, "raw_response": {"result": {"cibilData": {"GetCustomerAssetsResponse": {
        "GetCustomerAssetsSuccess": {"Asset": {
            "CreationDate": f"{date}T{hour:02d}:{mins}:00+05:30",
            "TrueLinkCreditReport": report}}}}}}}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    print(f"wrote {out_path}: {len(tradelines)} accounts, {len(enquiries)} enquiries")


if __name__ == "__main__":
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sample" / "report.pdf"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "tests" / "fixtures" / "reference_consumer.json"
    main(pdf, out)
