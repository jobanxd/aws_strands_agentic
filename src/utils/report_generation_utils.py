"""Utility classes for generating KYC final reports."""

import ast
from datetime import date, datetime, timezone
from typing import List, Literal, Optional, Union

from src.models.data_models import (
    PartyInfo,
    ProofOfIDData,
    EmploymentData,
    ProofOfAddressData,
)
from src.models.agent_models import (
    KYCQuestionAnswersWithEvidence,
    KYCnetFormDataWithEvidence,
    ComplianceCheckOutput,
)
from src.models.final_report_models import (
    LabelValueRow,
    LabelValueRowWithStatus,
    LabelValueRowReasonEvidence,
    EvidenceRef,
    AIAnswerItem,
    AIAnswerItemWithEvidence,
    EvidenceCheck,
    FinalReport,
    FinalReportInput,
)

StatusType = Literal["Verified", "Mismatch", "Unverified"]

# ---------------------------------------------------------------------------
# Evidence key constants — single source of truth for document keys
# ---------------------------------------------------------------------------
EV_PASSPORT = "passport"
EV_PROOF_OF_ADDRESS = "proof_of_address"
EV_PROOF_OF_EMPLOYMENT = "proof_of_employment"
EV_SERVICELINK = "servicelink"
EV_SVOC = "svoc"


class ReportGenerationUtils:
    """Utility class providing static methods for building KYC report data structures."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _ev(
        primary: str,
        supporting: Optional[List[str]] = None,
    ) -> EvidenceRef:
        """Convenience builder for EvidenceRef."""
        return EvidenceRef(primary=primary, supporting=supporting or [])

    # Drilldown Rows
    @staticmethod
    def build_kyc_drilldown_rows(data: PartyInfo) -> List[LabelValueRow]:
        """Build KYC drilldown rows from party info. Always verified from DB."""
        return [
            LabelValueRow(label="Party ID", value=str(data.party_id)),
            LabelValueRow(label="Party Name", value=data.party_name),
            LabelValueRow(label="Party Type", value=data.party_type),
            LabelValueRow(label="Current Review ID", value=str(data.review_id)),
            LabelValueRow(label="Current Review Type", value=data.current_review_type),
            LabelValueRow(
                label="Date Current Review Started",
                value=str(data.date_current_review_started),
            ),
            LabelValueRow(label="Last Manual Risk", value=data.last_manual_risk),
            LabelValueRow(label="Last Automated Risk", value=data.last_automated_risk),
        ]

    # Products Held Rows
    @staticmethod
    def build_kyc_info_servicelink_rows(
        data: KYCnetFormDataWithEvidence,
    ) -> List[Union[LabelValueRow,LabelValueRowReasonEvidence]]:
        """
        Build KYC info rows sourced from ServiceLink.
        Primary evidence: ServiceLink for all three fields.
        """


        ev_sl_svoc = ReportGenerationUtils._ev(
            primary=EV_SERVICELINK,
            supporting=[EV_SVOC],
        )

        return [
            LabelValueRowReasonEvidence(
                label="Type of Customer",
                value=data.type_of_customer.answer,
                reason=data.type_of_customer.reason,
                evidence=ev_sl_svoc,
            ),
            LabelValueRowReasonEvidence(
                label="Business Units with Account/Product",
                value=data.account_product.answer,
                reason=data.account_product.reason,
                evidence=ev_sl_svoc,
            ),
            LabelValueRow(
                label="Previous Review Risk Rating",
                value=data.previous_review_risk_rating.answer,
            ),
            LabelValueRowReasonEvidence(
                label="Account type/product(s) held",
                value=data.account_type_product.answer,
                reason=data.account_type_product.reason,
                evidence=ev_sl_svoc,
            ),
            LabelValueRowReasonEvidence(
                label="Products held by the customer",
                value=", ".join(data.products_held.answer),
                reason=data.products_held.reason,
                evidence=ev_sl_svoc,
            ),
            LabelValueRowReasonEvidence(
                label="Primary Account/Product identifier",
                value=str(data.primary_account_identifier.answer),
                reason=data.primary_account_identifier.reason,
                evidence=None,  # N/A — no document evidence
            ),
        ]

    # Identification Rows
    @staticmethod
    def build_kyc_info_rows(
        kyc_form_data: KYCnetFormDataWithEvidence,
    ) -> List[Union[LabelValueRowWithStatus, LabelValueRow, LabelValueRowReasonEvidence]]:
        """
        Build KYC info rows from form data and review info.
        Each field carries its own evidence reference based on the prompt logic.
        """

        # Evidence refs — built once, reused where the same field-group applies
        ev_passport = ReportGenerationUtils._ev(
            primary=EV_PASSPORT,
            supporting=[EV_SERVICELINK],
        )
        ev_passport_only = ReportGenerationUtils._ev(
            primary=EV_PASSPORT,
        )
        ev_addr = ReportGenerationUtils._ev(
            primary=EV_SERVICELINK,
            supporting=[EV_PROOF_OF_ADDRESS],
        )
        ev_servicelink = ReportGenerationUtils._ev(
            primary=EV_SERVICELINK,
        )

        rows = [
            # Title — sourced from ServiceLink (Account Name prefix / Customer Status)
            LabelValueRowWithStatus(
                label="Title",
                value=kyc_form_data.title.answer,
                status=kyc_form_data.title.status,
                reason=kyc_form_data.title.reason,
                evidence=ReportGenerationUtils._ev(
                    primary=EV_SERVICELINK,
                ),
            ),
            # Full name + individual parts — primary: passport
            LabelValueRowWithStatus(
                label="Full Name (First, Middle, Last)",
                value=kyc_form_data.full_name.answer,
                status=kyc_form_data.full_name.status,
                reason=kyc_form_data.full_name.reason,
                evidence=ev_passport,
            ),
            LabelValueRowWithStatus(
                label="First Name",
                value=kyc_form_data.first_name.answer,
                status=kyc_form_data.first_name.status,
                reason=kyc_form_data.first_name.reason,
                evidence=ev_passport,
            ),
            LabelValueRowWithStatus(
                label="Middle Name",
                value=kyc_form_data.middle_name.answer,
                status=kyc_form_data.middle_name.status,
                reason=kyc_form_data.middle_name.reason,
                evidence=ev_passport,
            ),
            LabelValueRowWithStatus(
                label="Last Name",
                value=kyc_form_data.last_name.answer,
                status=kyc_form_data.last_name.status,
                reason=kyc_form_data.last_name.reason,
                evidence=ev_passport,
            ),
            # DOB — primary: passport, supporting: svoc
            LabelValueRowWithStatus(
                label="Date of Birth",
                value=str(kyc_form_data.dob.answer),
                status=kyc_form_data.dob.status,
                reason=kyc_form_data.dob.reason,
                evidence=ReportGenerationUtils._ev(
                    primary=EV_PASSPORT,
                    supporting=[EV_SVOC],
                ),
            ),
            # Gender — primary: passport
            LabelValueRowWithStatus(
                label="Gender",
                value=kyc_form_data.gender.answer,
                status=kyc_form_data.gender.status,
                reason=kyc_form_data.gender.reason,
                evidence=ev_passport_only,
            ),
            # Address fields — primary: proof_of_address, supporting: servicelink
            LabelValueRowWithStatus(
                label="Registered Address",
                value=kyc_form_data.address.answer,
                status=kyc_form_data.address.status,
                reason=kyc_form_data.address.reason,
                evidence=ev_addr,
            ),
            LabelValueRow(
                label="Address Line 1",
                value=kyc_form_data.address_line_1.answer,
            ),
            LabelValueRow(
                label="Address Line 2",
                value=kyc_form_data.address_line_2.answer,
            ),
            LabelValueRow(
                label="Address Line 3",
                value=kyc_form_data.address_line_3.answer,
            ),
            # Post code + country of residence — primary: servicelink (DB source)
            LabelValueRowWithStatus(
                label="Post Code",
                value=kyc_form_data.post_code.answer,
                status=kyc_form_data.post_code.status,
                reason=kyc_form_data.post_code.reason,
                evidence=ev_servicelink,
            ),
            LabelValueRowWithStatus(
                label="Country of Residence",
                value=kyc_form_data.country_of_residence.answer,
                status=kyc_form_data.country_of_residence.status,
                reason=kyc_form_data.country_of_residence.reason,
                evidence=ev_servicelink,
            ),
            # Country of birth/citizenship — primary: passport only
            LabelValueRowWithStatus(
                label="Country of Birth",
                value=kyc_form_data.country_of_birth.answer,
                status=kyc_form_data.country_of_birth.status,
                reason=kyc_form_data.country_of_birth.reason,
                evidence=ev_passport_only,
            ),
            LabelValueRowWithStatus(
                label="Country of Citizenship",
                value=kyc_form_data.country_of_citizenship.answer,
                status=kyc_form_data.country_of_citizenship.status,
                reason=kyc_form_data.country_of_citizenship.reason,
                evidence=ev_passport_only,
            ),
            # Proof of true name — primary: passport
        ]

        if kyc_form_data.length_of_residence.answer is not None:
            rows.append(
                LabelValueRowReasonEvidence(
                    label="Length of Residence",
                    value=kyc_form_data.length_of_residence.answer,
                    reason=kyc_form_data.length_of_residence.reason,
                    evidence=ev_servicelink,
                )
            )

        return rows

    # Employment Rows
    @staticmethod
    def build_kyc_info_poe_rows(
        data: KYCnetFormDataWithEvidence,
    ) -> List[LabelValueRowWithStatus]:
        """Build KYC info rows for proof of employment. Primary: proof_of_employment."""

        ev_poe = ReportGenerationUtils._ev(
            primary=EV_SERVICELINK,
            supporting=[EV_PROOF_OF_EMPLOYMENT],
        )

        return [
            LabelValueRowWithStatus(
                label="Employment Status",
                value=data.employment_status.answer,
                status=data.employment_status.status,
                reason=data.employment_status.reason,
                evidence=ev_poe,
            ),
            LabelValueRowWithStatus(
                label="Occupation",
                value=data.occupation.answer,
                status=data.occupation.status,
                reason=data.occupation.reason,
                evidence=ev_poe,
            ),
            LabelValueRowWithStatus(
                label="Employer Name",
                value=(
                    data.employer_name.answer if data.employer_name.answer is not None else "None"
                ),
                status=data.employer_name.status,
                reason=data.employer_name.reason,
                evidence=ev_poe,
            ),
        ]

    # Proof of True Name Rows
    @staticmethod
    def build_kyc_info_pon_rows(
        data: KYCnetFormDataWithEvidence,
        proof_of_id: ProofOfIDData | None,
    ) -> List[LabelValueRowReasonEvidence]:
        """Build KYC info rows for proof of name. Primary: proof_of_id."""

        ev_pon = ReportGenerationUtils._ev(
            primary=EV_PASSPORT
        )

        if proof_of_id is None:
            name_document_value = "Additional information required"
        else:
            name_document_value = data.proof_of_true_name_verification.answer or "None"

        return [
            LabelValueRowReasonEvidence(
                label="Proof of True Name Verification Document",
                value=name_document_value,
                reason=data.proof_of_true_name_verification.reason,
                evidence=ev_pon,
            ),
        ]

    # Proof of Address Rows
    @staticmethod
    def build_kyc_info_poa_rows(
        data: KYCnetFormDataWithEvidence,
        proof_of_address: ProofOfAddressData | None,
    ) -> List[LabelValueRowWithStatus]:
        """Build KYC info rows for proof of address. Primary: proof_of_address."""

        ev_poa = ReportGenerationUtils._ev(
            primary=EV_PROOF_OF_ADDRESS
        )

        if proof_of_address is None:
            address_document_value = "Additional information required"
        else:
            address_document_value = data.proof_of_address_verification.answer or "None"

        return [
            LabelValueRowWithStatus(
                label="Proof of Address Verification Document",
                value=address_document_value,
                status=data.proof_of_address_verification.status,
                reason=data.proof_of_address_verification.reason,
                evidence=ev_poa,
            ),
        ]

    # ------------------------------------------------------------------
    # Question rows  (LabelValueRowWithStatus — with per-field evidence)
    # ------------------------------------------------------------------

    @staticmethod
    def build_kyc_qna_cash_percentage(
        data: KYCQuestionAnswersWithEvidence,
    ) -> List[AIAnswerItemWithEvidence]:
        """Build row for cash income percentage question. Primary: svoc."""
        return [
            AIAnswerItemWithEvidence(
                question=(
                    "What percentage of the customers income have been"
                    " generated as Cash in the past year?"
                ),
                answer=data.cash_income_percentage.answer,
                reason=data.cash_income_percentage.reason,
                evidence=ReportGenerationUtils._ev(
                    primary=EV_SVOC,
                )
            )
        ]

    @staticmethod
    def build_kyc_qna_transacted_outside_safe_country(
        data: KYCQuestionAnswersWithEvidence,
    ) -> List[AIAnswerItemWithEvidence]:
        """
        Build rows for outside-safe-country transaction and country risk questions.
        Primary: servicelink for all sub-questions.
        """

        def parse_dict_value(value):
            if value is None:
                return ""
            if isinstance(value, str):
                try:
                    return ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    return value
            return value

        rows = [
            AIAnswerItemWithEvidence(
                question=(
                    "Has the customer transacted with any Countries outside of the following"
                    " areas: EU/EEA/UK, North America or Australia/New Zealand?"
                ),
                answer="Yes" if data.transacted_outside_safe_countries.answer is True else "No",
                reason=data.transacted_outside_safe_countries.reason,
                evidence=ReportGenerationUtils._ev(
                    primary=EV_SERVICELINK,
                )
            )
        ]

        if data.transacted_outside_safe_countries.answer is True:
            rows.append(
                AIAnswerItemWithEvidence(
                    question=(
                        "Has the customer transacted with any of the following "
                        "High Risk Countries? What percentage of the customer's "
                        "total income was generated from each of the following countries?"
                    ),
                    answer=(
                        parse_dict_value(data.high_risk_countries_info.answer)
                        if data.high_risk_countries_info.answer is not None
                        else "No"
                    ),
                    reason=data.high_risk_countries_info.reason,
                    evidence=ReportGenerationUtils._ev(
                        primary=EV_SERVICELINK,
                )
                )
            )
            rows.append(
                AIAnswerItemWithEvidence(
                    question=(
                        "Has the customer transacted with any of the following Very High "
                        "Risk Countries? What percentage of the customer's total income "
                        "was generated from each of the following countries?"
                    ),
                    answer=(
                        parse_dict_value(data.very_high_risk_countries_info.answer)
                        if data.very_high_risk_countries_info.answer is not None
                        else "No"
                    ),
                    reason=data.very_high_risk_countries_info.reason,
                    evidence=ReportGenerationUtils._ev(
                        primary=EV_SERVICELINK,
                )
                )
            )
            rows.append(
                AIAnswerItemWithEvidence(
                    question=(
                        "Has the customer transacted with any of the following "
                        "Prohibited Countries?"
                    ),
                    answer=(
                        parse_dict_value(data.prohibited_countries_info.answer)
                        if data.prohibited_countries_info.answer is not None
                        else "No"
                    ),
                    reason=data.prohibited_countries_info.reason,
                    evidence=ReportGenerationUtils._ev(
                        primary=EV_SERVICELINK,
                )
                )
            )

        return rows

    # ------------------------------------------------------------------
    # Evidence checks and LLM responses (unchanged)
    # ------------------------------------------------------------------

    @staticmethod
    def build_llm_based_responses(
        data: KYCQuestionAnswersWithEvidence,
    ) -> List[AIAnswerItem]:
        """Build AI-assisted answer items from KYC question answers."""
        return [
            AIAnswerItem(
                question=(
                    "From account review, is there any evidence to suggest that previously"
                    " stated Source of Funds and Source of Wealth are no longer correct?"
                ),
                answer="Yes" if data.source_funds_wealth_changed.answer is True else "No",
                reason=data.source_funds_wealth_changed.reason or "",
            ),
            AIAnswerItem(
                question=(
                    "Does your review of the transactional activity on the account give rise"
                    " to any out of course or suspicious activity?"
                ),
                answer="Yes" if data.suspicious_activity_detected.answer is True else "No",
                reason=data.suspicious_activity_detected.reason or "",
            ),
            AIAnswerItem(
                question=(
                    "Is there any additional information that you want to add about the client"
                    " following your EDD/ODD review?"
                ),
                answer="Yes" if data.additional_information.answer is True else "No",
                reason=data.additional_information.reason or "",
            ),
            AIAnswerItem(
                question=(
                    "Is there anything resulting from your review of the customer and their"
                    " transactions that warrants escalation?"
                ),
                answer="Yes" if data.escalation_required.answer is True else "No",
                reason=data.escalation_required.reason or "",
            ),
        ]

    @staticmethod
    def build_passport_evidence_checks(
        id_data: ProofOfIDData,
        kyc_form_data: KYCnetFormDataWithEvidence,
    ) -> List[EvidenceCheck]:
        """Build evidence checks comparing ID document data against KYC profile."""
        return [
            EvidenceCheck(
                field="Name",
                document=id_data.name or "",
                profile=kyc_form_data.full_name.answer,
                match=kyc_form_data.full_name.status == "Verified",
            ),
            EvidenceCheck(
                field="DOB",
                document=str(id_data.dob) if id_data.dob is not None else "",
                profile=str(kyc_form_data.dob.answer),
                match=kyc_form_data.dob.status == "Verified",
            ),
            EvidenceCheck(
                field="Gender",
                document=str(id_data.gender) if id_data.dob is not None else "",
                profile=str(kyc_form_data.gender.answer),
                match=kyc_form_data.gender.status == "Verified",
            ),
            EvidenceCheck(
                field="Country of Birth",
                document=id_data.country_of_birth or "",
                profile=kyc_form_data.country_of_birth.answer,
                match=kyc_form_data.country_of_birth.status == "Verified",
            ),
        ]

    @staticmethod
    def build_poe_evidence_checks(
        employment_data: EmploymentData,
        kyc_form_data: KYCnetFormDataWithEvidence,
        ca_output: ComplianceCheckOutput,
    ) -> List[EvidenceCheck]:
        """Build evidence checks comparing proof-of-employment data against KYC profile."""
        return [
            EvidenceCheck(
                field="Employee Name",
                document=employment_data.employee_full_name or "",
                profile=kyc_form_data.full_name.answer,
                match=ca_output.employment_validation.is_full_name_matching,
            ),
            EvidenceCheck(
                field="Employment Status",
                document=(
                    str(employment_data.employment_status)
                    if employment_data.employment_status is not None
                    else ""
                ),
                profile=str(kyc_form_data.employment_status.answer),
                match=ca_output.employment_validation.is_employment_status_matching,
            ),
            EvidenceCheck(
                field="Employer Name",
                document=employment_data.employer or "",
                profile=kyc_form_data.employer_name.answer,
                match=ca_output.employment_validation.is_employer_matching,
            ),
        ]

    @staticmethod
    def build_proof_of_address_evidence_checks(
        address_data: ProofOfAddressData,
        kyc_form_data: KYCnetFormDataWithEvidence,
        ca_output: ComplianceCheckOutput,
    ) -> List[EvidenceCheck]:
        """Build evidence checks comparing proof-of-address data against KYC profile."""
        return [
            EvidenceCheck(
                field="Full Name",
                document=address_data.full_name or "",
                profile=kyc_form_data.full_name.answer,
                match=ca_output.proof_of_address_validation.is_full_name_matching,
            ),
            EvidenceCheck(
                field="Address",
                document=address_data.full_address or "",
                profile=kyc_form_data.address.answer,
                match=ca_output.proof_of_address_validation.is_full_address_matching,
            ),
        ]

    @staticmethod
    def build_servicelink_address_evidence_checks(
        servicelink: List[dict],
        kyc_form_data: KYCnetFormDataWithEvidence,
    ) -> List[EvidenceCheck]:
        """Build evidence checks comparing ServiceLink addresses against KYC profile."""

        addresses = []

        for idx, item in enumerate(servicelink, start=1):
            account_details = item.get("account_details", {})
            address = account_details.get("account_address")

            if address:
                addresses.append(f"Account {idx}: {address}")

        return [
            EvidenceCheck(
                field="Address",
                document=addresses,
                profile=kyc_form_data.address.answer,
                match=kyc_form_data.address.status == "Verified",
            )
        ]

    # ------------------------------------------------------------------
    # Main report assembly
    # ------------------------------------------------------------------

    @staticmethod
    async def final_report_generation(params: FinalReportInput = None, **kwargs) -> FinalReport:
        """Generate the final KYC report by assembling all data sections."""
        utc_now = datetime.now(timezone.utc)
        formatted_date = utc_now.strftime("%d/%m/%Y")

        if params is None:
            params = FinalReportInput(**kwargs)

        servicelink_list = [
            {
                "transactions": [t.model_dump() for t in item.transactions],
                "account_details": item.account_details.model_dump(),
            }
            for item in params.servicelink
        ]

            # Filter out closed accounts from svoc_data
        svoc_data_active = [account for account in params.svoc if account.closed != "Y"]

        # Filter servicelink_bundles to only keep bundles matching open accounts
        servicelink_active = [
            bundle for bundle in params.servicelink
            if any(
                account.agmt_id == bundle.account_details.agmt_id
                for account in svoc_data_active
            )
        ]

        servicelink_list_active = [
            {
                "transactions": [t.model_dump() for t in item.transactions],
                "account_details": item.account_details.model_dump(),
            }
            for item in servicelink_active
        ]

        svoc_list = []
        for item in params.svoc:
            svoc_dict = vars(item).copy()
            for k, v in svoc_dict.items():
                if isinstance(v, (date, datetime)):
                    svoc_dict[k] = str(v)
            svoc_list.append(svoc_dict)

        evidence_documents = []

        if params.textract_data.proof_of_id:
            evidence_documents.append(
                {
                    "key": "passport",
                    "label": "Identification",
                    "details": {
                        "title": (
                            f"ID Document - {params.textract_data.proof_of_id.name}"
                            f" ({params.textract_data.proof_of_id.country_of_birth})"
                        ),
                        "subtitle": f"Expires: {params.textract_data.proof_of_id.document_expiry}",
                    },
                    "preview": {
                        "type": "image",
                        "url": str(params.textract_data.proof_of_id.document_path),
                        "alt": "Identification document preview",
                    },
                    "checks": ReportGenerationUtils.build_passport_evidence_checks(
                        id_data=params.textract_data.proof_of_id,
                        kyc_form_data=params.kyc_form_data,
                    ),
                    "document_source": params.textract_data.proof_of_id.document_type,
                    "data_source": "Previous Review",
                }
            )

        if params.textract_data.employment:
            evidence_documents.append(
                {
                    "key": "proof_of_employment",
                    "label": "Proof of Employment",
                    "details": {
                        "title": "Proof of Employment",
                        "subtitle": f"Extracted: {formatted_date}",
                        "reason": "Supporting evidence",
                    },
                    "preview": {
                        "type": "image",
                        "url": str(params.textract_data.employment.document_path),
                        "alt": "Proof of employment document preview",
                    },
                    "checks": ReportGenerationUtils.build_poe_evidence_checks(
                        employment_data=params.textract_data.employment,
                        kyc_form_data=params.kyc_form_data,
                        ca_output=params.ca_output,
                    ),
                    "document_source": "COE",
                    "data_source": "ServiceLink",
                }
            )

        if params.textract_data.proof_of_address:
            evidence_documents.append(
                {
                    "key": "proof_of_address",
                    "label": "Proof of Address",
                    "details": {
                        "title": "Proof of Address",
                        "subtitle": f"Extracted: {formatted_date}",
                        "reason": "Supporting evidence",
                    },
                    "preview": {
                        "type": "image",
                        "url": str(params.textract_data.proof_of_address.document_path),
                        "alt": "Proof of address document preview",
                    },
                    "checks": ReportGenerationUtils.build_proof_of_address_evidence_checks(
                        address_data=params.textract_data.proof_of_address,
                        kyc_form_data=params.kyc_form_data,
                        ca_output=params.ca_output,
                    ),
                    "document_source": params.textract_data.proof_of_address.document_type,
                    "data_source": "Previous Review",
                }
            )

        evidence_documents.append(
            {
                "key": "servicelink",
                "label": "ServiceLink",
                "details": {
                    "title": "ServiceLink",
                    "subtitle": "ServiceLink",
                    "reason": "Supporting document",
                },
                "preview": {"type": "table", "content": servicelink_list, "alt": "ServiceLink"},
                "checks": ReportGenerationUtils.build_servicelink_address_evidence_checks(
                    servicelink=servicelink_list_active,
                    kyc_form_data=params.kyc_form_data
                ),
                "document_source": "ServiceLink",
                "data_source": "Previous Review",
            }
        )

        evidence_documents.append(
            {
                "key": "svoc",
                "label": "SVoC",
                "details": {"title": "SVoC", "subtitle": "SVoC", "reason": "Supporting document"},
                "cash_calculation": {"average_cash_percentage": f"{params.avg_cash_calc:.2f}%"},
                "preview": {"type": "table", "content": svoc_list, "alt": "SVoC"},
            }
        )

        report_dict = {
            "report_title": (
                f"{params.party_info.party_name} - {params.party_info.current_review_type}"
            ),
            "new_review_id": params.new_review_id,
            "overview": {"title": "Overview Summary", "bullets": []},
            "next_steps": [],
            "kycnet": {
                # Drilldown uses DrilldownCard — plain LabelValueRow, no status/evidence
                "drilldown": {
                    "title": "KYCNet Drilldown",
                    "cards": [
                        {
                            "rows": ReportGenerationUtils.build_kyc_drilldown_rows(
                                params.party_info
                            )
                        }
                    ],
                },
                # Information and Questions use Card with LabelValueRowWithStatus rows.
                # The card-level source label is kept for UI grouping; evidence is per-field.
                "information": {
                    "title": "KYCNet Information",
                    "cards": [
                        {
                            "section": "Accounts/Products Held",
                            "rows": ReportGenerationUtils.build_kyc_info_servicelink_rows(
                                params.kyc_form_data
                            ),
                        },
                        {
                            "section": "Identification",
                            "rows": ReportGenerationUtils.build_kyc_info_rows(
                                params.kyc_form_data,
                            ),
                        },
                        {
                            "section": "Proof of True Name",
                            "rows": ReportGenerationUtils.build_kyc_info_pon_rows(
                                params.kyc_form_data,
                                params.textract_data.proof_of_id,
                            ),
                        },
                        {
                            "section": "Proof of Address",
                            "rows": ReportGenerationUtils.build_kyc_info_poa_rows(
                                params.kyc_form_data,
                                params.textract_data.proof_of_address,
                            ),
                        },
                        {
                            "section": "Employment",
                            "rows": ReportGenerationUtils.build_kyc_info_poe_rows(
                                params.kyc_form_data,
                            ),
                        },
                    ],
                },
                "questions": {
                    "title": "KYCNet Question And Answer",
                    "cards": [
                        {
                            "section": "SVoC",
                            "rows": ReportGenerationUtils.build_kyc_qna_cash_percentage(
                                params.kyc_qna
                            ),
                        },
                        {
                            "section": "ServiceLink",
                            "rows": (
                                ReportGenerationUtils
                                .build_kyc_qna_transacted_outside_safe_country(params.kyc_qna)
                            ),
                        }
                    ],
                },
            },
            "llm_based_responses": {
                "title": "AI-Assisted KYC Answers",
                "items": ReportGenerationUtils.build_llm_based_responses(params.kyc_qna),
            },
            "evidence": {
                "documents": evidence_documents,
            },
        }

        return FinalReport.model_validate(report_dict)