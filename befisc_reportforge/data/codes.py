"""CIBIL / TransUnion code tables.

The TrueLink JSON delivered by the bureau usually carries only the code
(``symbol``) of an enumerated value and leaves ``description`` empty, so the
engine translates codes itself.  Tables follow the CIBIL TUEF / RBI uniform
credit-reporting format.  Where the reference PDF shows a particular spelling
(e.g. "Two wheeler Loan") that spelling is used.
"""

from __future__ import annotations

from typing import Mapping, Optional

ACCOUNT_TYPE: dict[str, str] = {
    "00": "Other",
    "01": "Auto Loan (Personal)",
    "02": "Housing Loan",
    "03": "Property Loan",
    "04": "Loan Against Shares/Securities",
    "05": "Personal Loan",
    "06": "Consumer Loan",
    "07": "Gold Loan",
    "08": "Education Loan",
    "09": "Loan to Professional",
    "10": "Credit Card",
    "11": "Leasing",
    "12": "Overdraft",
    "13": "Two wheeler Loan",
    "14": "Non-Funded Credit Facility",
    "15": "Loan Against Bank Deposits",
    "16": "Fleet Card",
    "17": "Commercial Vehicle Loan",
    "18": "Telco - Wireless",
    "19": "Telco - Broadband",
    "20": "Telco - Landline",
    "21": "Seller Financing",
    "22": "Seller Financing Soft",
    "23": "GECL Loan Secured",
    "24": "GECL Loan Unsecured",
    "31": "Secured Credit Card",
    "32": "Used Car Loan",
    "33": "Construction Equipment Loan",
    "34": "Tractor Loan",
    "35": "Corporate Credit Card",
    "36": "Kisan Credit Card",
    "37": "Loan on Credit Card",
    "38": "Prime Minister Jaan Dhan Yojana - Overdraft",
    "39": "Mudra Loans - Shishu / Kishor / Tarun",
    "40": "Microfinance - Business Loan",
    "41": "Microfinance - Personal Loan",
    "42": "Microfinance - Housing Loan",
    "43": "Microfinance - Others",
    "44": "Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme",
    "45": "P2P Personal Loan",
    "46": "P2P Auto Loan",
    "47": "P2P Education Loan",
    "50": "Business Loan - Secured",
    "51": "Business Loan - General",
    "52": "Business Loan - Priority Sector - Small Business",
    "53": "Business Loan - Priority Sector - Agriculture",
    "54": "Business Loan - Priority Sector - Others",
    "55": "Business Non-Funded Credit Facility - General",
    "56": "Business Non-Funded Credit Facility - Priority Sector - Small Business",
    "57": "Business Non-Funded Credit Facility - Priority Sector - Agriculture",
    "58": "Business Non-Funded Credit Facility - Priority Sector - Others",
    "59": "Business Loan Against Bank Deposits",
    "61": "Business Loan - Unsecured",
    "69": "Short Term Personal Loan",
    "70": "Priority Sector - Gold Loan",
    "71": "Temporary Overdraft",
}

# Enquiry purpose uses the account-type table.
ENQUIRY_PURPOSE = ACCOUNT_TYPE

OWNERSHIP: dict[str, str] = {
    "1": "Individual",
    "2": "Authorised User",
    "3": "Guarantor",
    "4": "Joint",
    "5": "Deceased",
}

TELEPHONE_TYPE: dict[str, str] = {
    "00": "Not Classified",
    "01": "Mobile Phone",
    "02": "Home Phone",
    "03": "Office Phone",
}

ADDRESS_CATEGORY: dict[str, str] = {
    "01": "Permanent Address",
    "02": "Residence Address",
    "03": "Office Address",
    "04": "Not Categorized",
    "05": "Address Not Available",
}

RESIDENCE_CODE: dict[str, str] = {
    "01": "Owned",
    "02": "Rented",
}

# TUEF numeric identification types (used for the raw-bureau fallback).
ID_TYPE_CODES: dict[str, str] = {
    "01": "TaxId",
    "02": "PassportId",
    "03": "VoterId",
    "04": "DriverLicense",
    "05": "RationCard",
    "06": "UID",
    "07": "AdditionalId1",
    "08": "AdditionalId2",
    "09": "CkycId",
    "10": "NregaCard",
}

# Display labels for identifier names.  Identifiers without an entry are shown
# with their raw name (the reference shows "SocialId", "VoterId", "CkycId").
ID_LABELS: dict[str, str] = {
    "TaxId": "INCOME TAX ID NUMBER (PAN)",
    "PAN": "INCOME TAX ID NUMBER (PAN)",
    "UID": "UNIVERSAL ID NUMBER (UID)",
    "UniversalId": "UNIVERSAL ID NUMBER (UID)",
    "NationalId": "UNIVERSAL ID NUMBER (UID)",
    "PassportId": "PASSPORT NUMBER",
    "DriverLicense": "DRIVING LICENSE NUMBER",
    "RationCard": "RATION CARD NUMBER",
}

# Identifiers listed first (in this order); everything else keeps input order.
ID_PRIORITY: tuple[str, ...] = (
    "INCOME TAX ID NUMBER (PAN)",
    "UNIVERSAL ID NUMBER (UID)",
    "PASSPORT NUMBER",
    "DRIVING LICENSE NUMBER",
    "RATION CARD NUMBER",
)

COLLATERAL_TYPE: dict[str, str] = {
    "00": "No Collateral",
    "01": "Property",
    "02": "Gold",
    "03": "Shares",
    "04": "Saving Account and Fixed Deposit",
    "05": "Multiple Securities",
    "06": "Others",
}

PAYMENT_FREQUENCY: dict[str, str] = {
    "01": "Weekly",
    "02": "Fortnightly",
    "03": "Monthly",
    "04": "Quarterly",
    "05": "Bullet Payment",
    "06": "Daily",
    "07": "Half Yearly",
    "08": "Yearly",
    "09": "On-demand",
}

SUIT_FILED: dict[str, str] = {
    "00": "No Suit Filed",
    "01": "Suit Filed",
    "02": "Wilful Default",
    "03": "Suit Filed (Wilful Default)",
}

CREDIT_FACILITY_STATUS: dict[str, str] = {
    "00": "Restructured Loan",
    "01": "Restructured Loan (Govt. Mandated)",
    "02": "Written-off",
    "03": "Settled",
    "04": "Post (WO) Settled",
    "05": "Account Sold",
    "06": "Written Off and Account Sold",
    "07": "Account Purchased",
    "08": "Account Purchased and Written Off",
    "09": "Account Purchased and Settled",
    "10": "Account Purchased and Restructured",
    "11": "Restructured due to Natural Calamity",
    "12": "Restructured due to COVID-19",
    "13": "Post Write Off Closed",
    "14": "Restructured & Closed",
    "15": "Auctioned & Settled",
    "16": "Repossessed & Settled",
    "17": "Guarantee Invoked",
}

OCCUPATION: dict[str, str] = {
    "01": "Salaried",
    "02": "Self Employed Professional",
    "03": "Self Employed",
    "04": "Others",
}

NET_GROSS_INDICATOR: dict[str, str] = {"G": "Gross Income", "N": "Net Income"}
MONTHLY_ANNUAL_INDICATOR: dict[str, str] = {"M": "Monthly", "A": "Annual"}

GENDER: dict[str, str] = {"1": "female", "2": "male", "3": "transgender"}

# Textual asset-classification values that may appear in DPD history.
ASSET_CLASSIFICATION_CODES = frozenset({"STD", "SUB", "DBT", "LSS", "SMA", "XXX", "SMA0", "SMA1", "SMA2"})

# Score-factor texts that carry no information.
NO_FACTOR_TEXTS = frozenset({"", "NO VALID FACTORS"})


def lookup(table: Mapping[str, str], code: Optional[str], *, fallback_raw: bool = True) -> str:
    """Translate ``code`` with ``table``.

    Codes are tried verbatim and with leading zeros normalised ("5" -> "05").
    Unknown codes return the raw code when ``fallback_raw`` is true, so data is
    never silently dropped; empty codes return ``""``.
    """
    if code is None:
        return ""
    code = str(code).strip()
    if not code:
        return ""
    if code in table:
        return table[code]
    if code.isdigit():
        for candidate in (code.zfill(2), code.lstrip("0") or "0"):
            if candidate in table:
                return table[candidate]
    return code if fallback_raw else ""
