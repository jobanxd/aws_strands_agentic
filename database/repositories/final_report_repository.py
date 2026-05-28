"""
Final report repository for KYC/ODD processing (SQLite version).
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from models.agent_models import (
    FinalReportParams,
    FinalReportUpdateParams,
)

logger = logging.getLogger(__name__)


class FinalReportRepository:
    """SQLite repository for final report creation and updates."""

    def __init__(self, ctx):
        self.config = ctx.config
        self.get_connection = ctx.get_connection

    # =========================
    # VALUE HELPERS
    # =========================

    def convert_value(self, value, is_date: bool = False) -> Any:
        result = value

        if is_date:
            if not value:
                return None
            if isinstance(value, str):
                try:
                    return datetime.strptime(value, "%Y-%m-%d").date()
                except Exception:
                    return None
            return value

        if value is None:
            return "N/A"
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)

        return str(value)

    def convert_answer_with_reason(self, answer_obj: Any) -> str:
        if not hasattr(answer_obj, "answer") or not hasattr(answer_obj, "reason"):
            return self.convert_value(answer_obj)

        answer = answer_obj.answer
        reason = answer_obj.reason or ""

        if isinstance(answer, bool):
            answer_str = "Yes" if answer else "No"
        elif answer is None:
            answer_str = "N/A"
        elif isinstance(answer, list):
            answer_str = ", ".join(str(v) for v in answer)
        else:
            answer_str = str(answer)

        return f"{answer_str} - {reason}" if reason.strip() else answer_str

    # =========================
    # SAVE FINAL REPORT
    # =========================

    async def save_final_report(
        self,
        params: Optional[FinalReportParams] = None,
        **kwargs,
    ) -> bool:

        if params is None and not kwargs:
            raise ValueError("Either params or keyword arguments must be provided.")

        if params is None:
            params = FinalReportParams(**kwargs)

        try:
            query = """
            INSERT INTO final_report (
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
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
            )
            """

            async with self.get_connection() as conn:
                await conn.execute(
                    query,
                    (
                        params.new_review_id,
                        params.party_id,
                        params.session_id,
                        params.process_id,

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

                        self.convert_value(params.overview_summary) if params.overview_summary else None,
                        self.convert_value(params.next_steps) if params.next_steps else None,
                    ),
                )
                await conn.commit()

            logger.info(
                "Saved final report for party_id=%s review_id=%s",
                params.party_id,
                params.new_review_id,
            )
            return True

        except Exception as e:
            logger.error("Failed to save final report: %s", e, exc_info=True)
            return False

    # =========================
    # UPDATE FINAL REPORT
    # =========================

    async def update_final_report_fields(
        self,
        params: Optional[FinalReportUpdateParams] = None,
        **kwargs,
    ) -> bool:

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

        filtered = {
            k: v for k, v in params.updates.items() if k in allowed_fields
        }

        if not filtered:
            logger.warning(
                "No valid fields to update for session %s review %s",
                params.session_id,
                params.review_id,
            )
            return False

        try:
            set_clause = ", ".join([f"{k} = ?" for k in filtered.keys()])

            query = f"""
            UPDATE final_report
            SET {set_clause}
            WHERE session_id = ?
              AND new_review_id = ?
            """

            values = list(filtered.values())
            values.extend([params.session_id, params.review_id])

            async with self.get_connection() as conn:
                cursor = await conn.execute(query, tuple(values))
                await conn.commit()

                rows_updated = cursor.rowcount if hasattr(cursor, "rowcount") else 0

            if rows_updated > 0:
                logger.info(
                    "Updated final_report fields for session %s review %s",
                    params.session_id,
                    params.review_id,
                )
                return True

            return False

        except Exception as e:
            logger.error("Error updating final_report: %s", e, exc_info=True)
            return False

    # =========================
    # GET ALL REPORTS
    # =========================

    async def get_all_final_reports(self) -> List[Dict[str, Any]]:

        query = """
        SELECT *
        FROM final_report
        ORDER BY created_at DESC
        """

        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(query)
                rows = await cursor.fetchall()

            results = [dict(row) for row in rows]
            logger.info("Retrieved %s final reports", len(results))
            return results

        except Exception as e:
            logger.error("Error fetching final reports: %s", e, exc_info=True)
            return []

    # =========================
    # GET SINGLE REPORT
    # =========================

    async def get_final_report(
        self,
        session_id: str,
        review_id: str,
    ) -> Optional[Dict[str, Any]]:

        query = """
        SELECT *
        FROM final_report
        WHERE session_id = ?
          AND new_review_id = ?
        """

        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(query, (session_id, review_id))
                row = await cursor.fetchone()

            if not row:
                return None

            return dict(row)

        except Exception as e:
            logger.error("Error fetching final report: %s", e, exc_info=True)
            return None
