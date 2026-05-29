"""Models for Data for ODD Review"""
from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel, field_validator

# ----------------------------- SharePoint Models ----------------------------- #


class SharePointListItem(BaseModel):
    """SharePoint list item"""

    party_id: str  # PARTY_ID
    old_review_id: Optional[str] = None  # OLD_REVIEW_ID
    new_review_id: Optional[str] = None  # NEW_REVIEW_ID
    risk: Optional[str] = None  # RISK
    next_review_date: Optional[date] = None  # NEXT_REVIEW_DATE
    review_type: Optional[str] = None  # REVIEW_TYPE
    review_status: Optional[str] = None  # REVIEW_STATUS
    review_completion_date: Optional[date] = None  # REVIEW_COMPLETION_DATE


# ----------------------------- Dashboard Data Models----------------------------- #
class DashboardItem(BaseModel):
    """SharePoint list item"""

    party_id: Optional[str] = None
    party_name: Optional[str] = None
    latest_completed_review_id: Optional[str] = None
    previous_completed_review_id: Optional[str] = None
    review_type: Optional[str] = None
    current_risk: Optional[str] = None
    next_review_date: Optional[str | date] = None
    review_completion_date: Optional[str | date] = None
    last_review_date: Optional[str | date] = None
    review_status: Optional[str] = None
    process_id: Optional[str] = None


# ----------------------------- KYCnet Info Models----------------------------- #


class PartyInfo(BaseModel):
    """Party information from KYCnet extract - matches kycnet_drilldown table"""

    entrp_party_ident: str  # ENTRP_PRTY_IDENT
    party_id: str  # PARTY_ID
    review_id: str  # REVIEW_ID
    party_name: str  # CUST_NAME
    party_type: Optional[str] = None  # TYPE_OF_CUSTOMER
    current_review_type: Optional[str] = None  # WORKFLOW
    date_current_review_started: date  # REVIEW_CREATED
    current_review_step: Optional[str] = None  # CURRENT_STEP
    last_manual_risk: Optional[str] = None  # ASSESSMENT_RISK
    last_automated_risk: Optional[str] = None  # Previous Review Risk Rating


class ReviewInfo(BaseModel):
    """Review information from kycnet_reviews table - includes all KYCnet form fields"""

    entrp_party_ident: str  # ENTRP_PRTY_IDENT
    review_tag: Optional[str] = None  # REVIEW_TAG
    review_id: str  # REVIEW_ID

    # Personal Information
    type_of_customer: Optional[str] = None  # TYPE_OF_CUSTOMER
    business_units: Optional[str] = None  # Business Units the Customer holds and Account/Product
    previous_review_risk_rating: Optional[str] = None  # Previous Review Risk Rating
    title: Optional[str] = None  # title1
    full_name: Optional[str] = None  # CUST_NAME
    first_name: Optional[str] = None  # first_name
    middle_name: Optional[str] = None  # middle_name
    last_name: Optional[str] = None  #last_name
    date_of_birth: Optional[date] = None  # DOB
    gender: Optional[str] = None  # Gender

    # Address Information
    address_line_1: Optional[str] = None  # Address_line_1
    address_line_2: Optional[str] = None  # Address_line_2
    address_line_3: Optional[str] = None  # Address_line_3
    post_code: Optional[str] = None  # Post code
    country_of_residence: Optional[str] = None  # Country of Residence
    country_of_birth: Optional[str] = None  # Country of Birth
    country_of_citizenship: Optional[str] = None  # Country of Citizenship
    length_of_residence: Optional[str] = None  # Length of Residence in Ireland

    # Employment Information
    employment_status: Optional[str] = None  # Employment  Status
    occupation: Optional[str] = None  # Occupation
    employer_name: Optional[str] = None  # Employer Name

    # Account Information
    account_type_product: Optional[str] = None  # Account Type Product
    products_held: Optional[str] = None  # Please provide details of all products held by customer
    primary_account_identifier: Optional[str] = None

    # Questions and Answers
    cash_income_percentage: Optional[str] = None
    transacted_outside_safe_countries: Optional[str] = None
    high_risk_countries_info: Optional[str] = None
    very_high_risk_countries_info: Optional[str] = None
    prohibited_countries_info: Optional[str] = None
    source_funds_wealth_changed: Optional[str] = None
    suspicious_activity_detected: Optional[str] = None
    additional_information: Optional[str] = None
    escalation_required: Optional[str] = None


# ----------------------------- Textract Models ----------------------------- #


class ProofOfIDData(BaseModel):
    """Data extracted from identification documents"""

    party_id: str
    review_id: str
    document_type: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None  # Keep original format from document (e.g., "22 Mar 1985")
    gender: Optional[str] = None
    country_of_birth: Optional[str] = None
    country_of_citizenship: Optional[str] = None
    nationality: Optional[str] = None
    document_expiry: Optional[str] = None
    document_path: Optional[str] = None


class EmploymentData(BaseModel):
    """Data extracted from Certificate of Employment documents"""

    party_id: str
    review_id: str
    employee_full_name: Optional[str] = None
    employment_status: Optional[str] = None
    employer: Optional[str] = None
    document_path: Optional[str] = None


class ProofOfAddressData(BaseModel):
    """Data extracted from proof of address documents"""

    party_id: str
    review_id: str
    document_type: Optional[str] = None
    full_name: Optional[str] = None
    full_address: Optional[str] = None
    document_path: Optional[str] = None


class TextractData(BaseModel):
    """Combined data extracted from all documents using Textract"""

    party_id: str
    review_id: str
    proof_of_id: Optional[ProofOfIDData] = None
    employment: Optional[EmploymentData] = None
    proof_of_address: Optional[ProofOfAddressData] = None


# ----------------------------- SvoC Extract Models ----------------------------- #


class SvoCExtract(BaseModel):
    """SvoC extract data - matches svoc_extracts table"""

    entrp_party_ident: str  # ENTRP_PRTY_IDENT
    agmt_id: str  # AGMT_ID
    nsc: Optional[str] = None  # EBRN_NSC
    account_no: Optional[str] = None  # EAC_NO
    con_acct_num: Optional[str] = None  # CON_ACCT_NUM

    name: Optional[str]  # PRTY_NAME
    address: Optional[str]  # ADDRESS
    dob: Optional[date]  # BRTH_DT
    postcode: Optional[str] = None  # SRC_ADRS_PST_CD
    cash_percentage: Optional[float] = None  # CASH %
    turnover_selected: Optional[float] = None  # TOTAL_TURNOVER
    source_system: Optional[str] = None  # DATA_SRC_CD
    product: Optional[str] = None  # AGMT_TYP_CD

    closed: Optional[str] = None  # CLOSED
    closure_date: Optional[date] = None  # AGMT_CLSE_DTTM
    gp_indicator: Optional[str] = None  # GP INDICATOR

    @field_validator("cash_percentage")
    @classmethod
    def round_cash_percentage(cls, v: Optional[float]) -> Optional[float]:
        """Round cash percentage always to 2 decimal places"""
        if v is not None:
            return round(v, 2)
        return v

# ----------------------------- ServiceLink Models ----------------------------- #


class ServiceLinkTransaction(BaseModel):
    """Individual transaction from servicelink_transactions table"""

    agmt_id: str
    account_no: str
    nsc: str

    transaction_date: Optional[date] = None

    src: Optional[str] = None
    tx_narrative: Optional[str] = None
    debit_eur: Optional[float] = None
    credit_eur: Optional[float] = None
    tx_code: Optional[str] = None
    country_of_origin: Optional[str] = None

    @field_validator("transaction_date", mode="before")
    @classmethod
    def parse_transaction_date(cls, v):
        if v is None or v == "":
            return None

        if isinstance(v, date):
            return v

        formats = [
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                continue

        raise ValueError(f"Unsupported date format: {v}")

    @field_validator("debit_eur", "credit_eur")
    @classmethod
    def round_to_two_decimals(cls, v):
        if v is not None:
            return round(v, 2)
        return v


class ServiceLinkAccountDetails(BaseModel):
    """ServiceLink account details - matches servicelink_accounts_details table"""

    agmt_id: str  # AGMT_ID
    account_type: Optional[str] = None  # AGMT_TYP_CD
    account_name: Optional[str] = None  # PRTY_NAME
    account_address: Optional[str] = None  # ADDRESS
    post_code: Optional[str] = None  # SRC_ADRS_PST_CD
    non_resident_code: Optional[str] = None  # NRES_CDE


class ServiceLinkBundle(BaseModel):
    """ServiceLinkBundled"""
    account_details: ServiceLinkAccountDetails
    transactions: List[ServiceLinkTransaction]
    transaction_codes: List[ServiceLinkTransaction]
