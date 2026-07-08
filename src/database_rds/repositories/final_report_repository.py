"""
Final report repository for KYC/ODD processing.

This module provides database operations for creating, updating,
and retrieving final KYC reports generated during the ODD workflow.
It also includes helper utilities for converting form values and
formatting question answers for database storage.

These repository methods are composed into the
ODDDatabaseManagerPostgreSQL class and rely on its database
connection management.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import asyncpg

from src.models.agent_models import (
    FinalReportParams,
    FinalReportUpdateParams,
)

logger = logging.getLogger(__name__)


class FinalReportRepository:
    """Repository methods for final report creation and updates."""

    def __init__(self, ctx):
        """Initialize the repository with the database manager context."""
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    def convert_value(self, value, is_date: bool = False) -> Any:
        """Convert values for database storage."""
        result = value

        if is_date:
            if not value:
                result = None
            elif isinstance(value, str):
                try:
                    result = datetime.strptime(value, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    result = None

        else:
            if value is None:
                result = "N/A"
            elif isinstance(value, bool):
                result = "Yes" if value else "No"
            elif isinstance(value, list):
                result = ", ".join(str(item) for item in value)
            else:
                result = str(value)

        return result

    def convert_answer_with_reason(self, answer_obj: Any) -> str:
        """Convert AnswerWithEvidence object to 'answer - reason' format."""
        if not hasattr(answer_obj, "answer") or not hasattr(answer_obj, "reason"):
            return self.convert_value(answer_obj)

        answer = answer_obj.answer
        reason = answer_obj.reason or ""

        # Convert answer to string
        if isinstance(answer, bool):
            answer_str = "Yes" if answer else "No"
        elif answer is None:
            answer_str = "N/A"
        elif isinstance(answer, list):
            answer_str = ", ".join(str(item) for item in answer)
        else:
            answer_str = str(answer)

        # Combine answer and reason
        if reason.strip():
            return f"{answer_str} - {reason}"

        return answer_str

    async def save_final_report(
        self,
        params: Optional[FinalReportParams] = None,
        **kwargs,
    ) -> bool:
        """
        Save final KYC report to the dev.final_report table.

        Args:
            party_id: Party identifier
            new_review_id: Review identifier
            session_id: Session identifier
            process_id: Process identifier
            kyc_form_data: KYC form data with all customer information fields
            kyc_question_answers: KYC question answers

        Returns:
            bool: True if successful, False otherwise
        """
        if params is None and not kwargs:
            raise ValueError("Either params or keyword arguments must be provided.")

        if params is None:
            params = FinalReportParams(**kwargs)

        try:
            # Build the insert query with all fields
            query = f"""
            INSERT INTO {self.config.db_schema}.final_report (
                new_review_id,
                party_id,
                session_id,
                process_id,
                type_of_customer,
                account_product,
                previous_review_risk_rating,
                title,
                full_name,
                dob,
                gender,
                address,
                post_code,
                country_of_residence,
                country_of_birth,
                country_of_citizenship,
                length_of_residence,
                employment_status,
                occupation,
                employer_name,
                account_type_product,
                products_held,
                primary_account_identifier,
                cash_income_percentage,
                transacted_outside_safe_countries,
                high_risk_countries_info,
                very_high_risk_countries_info,
                prohibited_countries_info,
                source_funds_wealth_changed,
                suspicious_activity_detected,
                additional_information,
                escalation_required,
                overview_summary,
                next_steps,
                created_at
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24,
                $25, $26, $27, $28, $29, $30, $31, $32, $33, $34, CURRENT_TIMESTAMP
            )
            """

            async with self.get_connection() as conn:
                await conn.execute(
                    query,
                    params.new_review_id,
                    params.party_id,
                    params.session_id,
                    params.process_id,
                    # KYC Form Data fields
                    self.convert_value(params.kyc_form_data.type_of_customer.answer),
                    self.convert_value(params.kyc_form_data.account_product.answer),
                    self.convert_value(params.kyc_form_data.previous_review_risk_rating.answer),
                    self.convert_value(params.kyc_form_data.title.answer),
                    self.convert_value(params.kyc_form_data.full_name.answer),
                    self.convert_value(params.kyc_form_data.dob.answer, is_date=True),
                    self.convert_value(params.kyc_form_data.gender.answer),
                    self.convert_value(params.kyc_form_data.address.answer),
                    self.convert_value(params.kyc_form_data.post_code.answer),
                    self.convert_value(params.kyc_form_data.country_of_residence.answer),
                    self.convert_value(params.kyc_form_data.country_of_birth.answer),
                    self.convert_value(params.kyc_form_data.country_of_citizenship.answer),
                    self.convert_value(params.kyc_form_data.length_of_residence.answer),
                    self.convert_value(params.kyc_form_data.employment_status.answer),
                    self.convert_value(params.kyc_form_data.occupation.answer),
                    self.convert_value(params.kyc_form_data.employer_name.answer),
                    self.convert_value(params.kyc_form_data.account_type_product.answer),
                    self.convert_value(params.kyc_form_data.products_held.answer),
                    self.convert_value(params.kyc_form_data.primary_account_identifier.answer),
                    # KYC Question Answers - now with reason appended
                    self.convert_answer_with_reason(
                        params.kyc_question_answers.cash_income_percentage
                    ),
                    self.convert_answer_with_reason(
                        params.kyc_question_answers.transacted_outside_safe_countries
                    ),
                    self.convert_answer_with_reason(
                        params.kyc_question_answers.high_risk_countries_info
                    ),
                    self.convert_answer_with_reason(
                        params.kyc_question_answers.very_high_risk_countries_info
                    ),
                    self.convert_answer_with_reason(
                        params.kyc_question_answers.prohibited_countries_info
                    ),
                    self.convert_answer_with_reason(
                        params.kyc_question_answers.source_funds_wealth_changed
                    ),
                    self.convert_answer_with_reason(
                        params.kyc_question_answers.suspicious_activity_detected
                    ),
                    self.convert_answer_with_reason(
                        params.kyc_question_answers.additional_information
                    ),
                    self.convert_answer_with_reason(
                        params.kyc_question_answers.escalation_required
                    ),
                    (
                        self.convert_value(params.overview_summary)
                        if params.overview_summary
                        else None
                    ),
                    self.convert_value(params.next_steps) if params.next_steps else None,
                )

            logger.info(
                "Successfully saved final report for party_id=%s, review_id=%s",
                params.party_id,
                params.new_review_id,
            )
            return True

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Failed to save final report for party_id=%s: %s",
                params.party_id,
                e,
                exc_info=True,
            )
            return False

    def _parse_modified_at(self, modified_at: Optional[str]):
        """Parse modified_at into a datetime object when needed."""
        if modified_at is None:
            return None
        if isinstance(modified_at, str):
            return datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
        return modified_at

    def _build_final_report_update_query(
        self,
        filtered_updates: Dict[str, str],
        modified_by: Optional[str],
        modified_at,
    ) -> tuple[str, list]:
        """Build the dynamic UPDATE query and its parameter list."""
        param_num = 3
        set_clauses = []

        for field in filtered_updates:
            set_clauses.append(f"{field} = ${param_num}")
            param_num += 1

        if modified_by is not None:
            set_clauses.append(f"modified_by = ${param_num}")
            param_num += 1

        if modified_at is not None:
            set_clauses.append(f"modified_at = ${param_num}")
            param_num += 1

        query = f"""
        UPDATE {self.config.db_schema}.final_report
        SET {", ".join(set_clauses)}
        WHERE session_id = $1 AND new_review_id = $2
        """
        return query, set_clauses

    async def update_final_report_fields(
        self,
        params: Optional[FinalReportUpdateParams] = None,
        **kwargs,
    ) -> bool:
        """Update selected fields in the final_report table."""
        if params is None and not kwargs:
            raise ValueError("Either params or keyword arguments must be provided.")

        if params is None:
            params = FinalReportUpdateParams(**kwargs)

        allowed_fields = {
            "source_funds_wealth_changed",
            "suspicious_activity_detected",
            "additional_information",
            "escalation_required",
        }

        filtered_updates = {
            key: value for key, value in params.updates.items() if key in allowed_fields
        }

        if not filtered_updates:
            logger.warning(
                "No valid fields to update for session %s, review %s",
                params.session_id,
                params.review_id,
            )
            return False

        try:
            modified_at_dt = self._parse_modified_at(params.modified_at)
            query, _ = self._build_final_report_update_query(
                filtered_updates,
                params.modified_by,
                modified_at_dt,
            )

            query_params = [
                params.session_id,
                params.review_id,
                *filtered_updates.values(),
            ]

            if params.modified_by is not None:
                query_params.append(params.modified_by)

            if modified_at_dt is not None:
                query_params.append(modified_at_dt)

            async with self.get_connection() as conn:
                result = await conn.execute(query, *query_params)

            rows_updated = int(result.split()[-1]) if result else 0
            if rows_updated > 0:
                logger.info(
                    "Updated %s fields in final_report for session %s, review %s",
                    len(filtered_updates),
                    params.session_id,
                    params.review_id,
                )
                return True

            logger.warning(
                "No final_report found for session %s, review %s",
                params.session_id,
                params.review_id,
            )
            return False

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Error updating final_report fields: %s",
                e,
                exc_info=True,
            )
            return False

    async def get_all_final_reports(self) -> List[Dict[str, Any]]:
        """
        Get all final reports from the final_report table.
        Returns all fields from the final_report table.

        Returns:
            List of dictionaries containing all final report fields
        """
        try:
            query = f"""
            SELECT
                new_review_id,
                party_id,
                session_id,
                process_id,
                overview_summary,
                next_steps,
                type_of_customer,
                account_product,
                previous_review_risk_rating,
                title,
                full_name,
                dob,
                gender,
                address,
                post_code,
                country_of_residence,
                country_of_birth,
                country_of_citizenship,
                length_of_residence,
                employment_status,
                occupation,
                employer_name,
                account_type_product,
                products_held,
                primary_account_identifier,
                cash_income_percentage,
                transacted_outside_safe_countries,
                high_risk_countries_info,
                very_high_risk_countries_info,
                prohibited_countries_info,
                source_funds_wealth_changed,
                suspicious_activity_detected,
                additional_information,
                escalation_required,
                created_at,
                created_by,
                modified_at,
                modified_by
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY party_id
                        ORDER BY created_at DESC
                    ) as rn
                FROM {self.config.db_schema}.final_report
            ) ranked
            WHERE rn = 1
            ORDER BY created_at ASC
            """

            async with self.get_connection() as conn:
                rows = await conn.fetch(query)

                results = []
                for row in rows:
                    row_dict = dict(row)
                    # Convert date/datetime objects to strings for JSON/CSV serialization
                    if row_dict.get("dob") and hasattr(row_dict["dob"], "isoformat"):
                        row_dict["dob"] = row_dict["dob"].isoformat()
                    if row_dict.get("created_at") and hasattr(row_dict["created_at"], "isoformat"):
                        row_dict["created_at"] = row_dict["created_at"].isoformat()
                    results.append(row_dict)

                logger.info("Retrieved %s final reports.", len(results))
                return results

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Error retrieving final reports: %s",
                e,
                exc_info=True,
            )
            return []

    async def get_final_report(self, session_id: str, review_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the final report for a given session_id and review_id.

        Args:
            session_id: Session identifier
            review_id: Review identifier

        Returns:
            Dictionary containing final report fields, or None if not found
        """
        try:
            query = f"""
            SELECT
                session_id,
                new_review_id,
                source_funds_wealth_changed,
                suspicious_activity_detected,
                additional_information,
                escalation_required
            FROM {self.config.db_schema}.final_report
            WHERE session_id = $1 AND new_review_id = $2
            """

            async with self.get_connection() as conn:
                row = await conn.fetchrow(query, session_id, review_id)

                if row:
                    result = dict(row)
                    logger.info(
                        "Retrieved final_report for session %s, review %s",
                        session_id,
                        review_id,
                    )
                    return result

                logger.warning(
                    "No final_report found for session %s, review %s",
                    session_id,
                    review_id,
                )
                return None

        except (asyncpg.PostgresError, OSError, ConnectionError, TimeoutError) as e:
            logger.error(
                "Error retrieving final_report for session %s, review %s: %s",
                session_id,
                review_id,
                e,
                exc_info=True,
            )
            return None
