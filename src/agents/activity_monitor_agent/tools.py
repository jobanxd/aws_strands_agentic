"""
Tools under the Activity Monitor Agent
"""

import json
import asyncio

from strands import tool
from typing import Dict
from strands import Agent

from src.core.model_factory import get_model
from src.workflows.state import PipelineState
from src.utils.logger import get_logger

logger = get_logger(__name__)


def make_tools(state: PipelineState) -> list:
    """
    Returns all Activity Monitor Agent tools bound to given pipeline state.
    """

    @tool
    def filter_active_accounts(party_id: str) -> str:
        """
        Filter out closed accounts from svoc_data and servicelink_bundles.
        Only keep bundles that match open accounts.
        Must be called first before any analysis.
        """
        if not state.svoc_data:
            return json.dumps({"error": "SVoC data not in state. DataAnalyst must run first.", "status": "failed"})

        open_svoc = [s for s in state.svoc_data if (s.closed or "N").upper() != "Y"]
        open_agmt_ids = {s.agmt_id for s in open_svoc}

        active_bundles = [
            b for b in (state.servicelink_bundles or [])
            if b.account_details.agmt_id in open_agmt_ids
        ]

        # Store filtered data back into state so subsequent tools use it
        state.active_svoc_data = open_svoc
        state.active_servicelink_bundles = active_bundles
        state.mark_step("filter_active_accounts")

        logger.info(f"Active accounts: {len(open_svoc)}, Active bundles: {len(active_bundles)}")
        return json.dumps({
            "party_id": party_id,
            "open_accounts": len(open_svoc),
            "active_bundles": len(active_bundles),
            "status": "ok",
        })

    @tool
    def analyze_employment(party_id: str) -> str:
        """
        Analyze employment status from transaction history for all active bundles.
        Calls an internal LLM agent per bundle to determine employment status and employer.
        Saves results directly to state.
        """
        async def _analyze():
            if not state.active_servicelink_bundles:
                return {"error": "No active bundles. Run filter_active_accounts first.", "status": "failed"}

            prompt_template = await state.db.agent.get_agent_prompt(6.0)
            if not prompt_template:
                return {"error": "Employment analysis prompt not found in database.", "status": "failed"}

            results = []
            for bundle in state.active_servicelink_bundles:
                if not bundle.account_details or not bundle.transactions:
                    results.append({
                        "account_no": "Additional information required",
                        "nsc": "Additional information required",
                        "employment_status": "Additional information required",
                        "employment_status_reasoning": "No transaction history found",
                        "employer": "Additional information required",
                        "employer_reasoning": "No transaction history found",
                        "employment_reason": "No transaction history found",
                        "employment_recommendation": "Review transaction for this account",
                    })
                    continue

                transaction_list = [t.model_dump() for t in bundle.transactions]
                prompt = prompt_template.format(
                    transaction=json.dumps(transaction_list, default=str)
                )

                # Internal LLM agent call — replaces your original async_completion
                analysis_agent = Agent(
                    system_prompt="""You are a financial analyst. 
                    Analyze the provided transactions and return ONLY a valid JSON object.
                    No explanation. No markdown. No code blocks. Raw JSON only.""",
                    model=get_model(),
                )

                try:
                    response = str(analysis_agent(prompt))
                    # Strip any markdown fences the model might add
                    response = response.strip().strip("```json").strip("```").strip()
                    result = json.loads(response)
                    results.append({
                        "account_no": bundle.transactions[0].account_no,
                        "nsc": bundle.transactions[0].nsc,
                        "employment_status": result.get("employment_status", "Unknown"),
                        "employment_status_reasoning": result.get("employment_status_reasoning", ""),
                        "employer": result.get("employer"),
                        "employer_reasoning": result.get("employer_reasoning", ""),
                        "employment_reason": result.get("employment_reason", ""),
                        "employment_recommendation": result.get("employment_recommendation", ""),
                    })
                    logger.info(f"Employment analyzed for account: {bundle.transactions[0].account_no}")
                except (json.JSONDecodeError, Exception) as exc:
                    logger.error(f"Employment analysis failed for bundle: {exc}")
                    results.append({
                        "account_no": bundle.transactions[0].account_no if bundle.transactions else "Unknown",
                        "nsc": bundle.transactions[0].nsc if bundle.transactions else "Unknown",
                        "employment_status": "Additional information required",
                        "employment_status_reasoning": f"Analysis failed: {exc}",
                        "employer": None,
                        "employer_reasoning": "",
                        "employment_reason": str(exc),
                        "employment_recommendation": "Manual review required",
                    })

            # Save directly to state — no separate save tool needed
            state.employment_analysis_results = results
            state.mark_step("analyze_employment")

            logger.info(f"Employment analysis complete: {len(results)} accounts")
            return {"status": "ok", "accounts_analyzed": len(results)}

        try:
            result = asyncio.run(_analyze())
            return json.dumps(result, default=str)
        except Exception as exc:
            logger.error(f"analyze_employment failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})

    @tool
    def analyze_country_risk(party_id: str) -> str:
        """
        Analyze ServiceLink transaction bundles for international transactions.
        Detects transactions with tx_code=931 and GP indicator, then categorizes
        countries into high risk, very high risk, and prohibited.
        Pure logic — no LLM call needed.
        Must be called after filter_active_accounts.
        """
        async def _analyze():
            if not state.active_servicelink_bundles:
                return {"error": "No active bundles. Run filter_active_accounts first.", "status": "failed"}

            high_risk = await state.db.country_risk.get_high_risk_countries()
            very_high = await state.db.country_risk.get_very_high_risk_countries()
            prohibited = await state.db.country_risk.get_prohibited_countries()

            # Build lookup map
            country_risk_map: Dict[str, str] = {}
            for c in high_risk:
                country_risk_map[c] = "high_risk_countries"
            for c in very_high:
                country_risk_map[c] = "very_high_risk_countries"
            for c in prohibited:
                country_risk_map[c] = "prohibited_countries"

            result = {
                "transacted_outside_safe_countries": False,
                "high_risk_countries": {},
                "very_high_risk_countries": {},
                "prohibited_countries": {},
            }

            for bundle in state.active_servicelink_bundles:
                transactions = bundle.transaction_codes if hasattr(bundle, "transaction_codes") else bundle.transactions or []
                tx_list = [t.model_dump() for t in transactions] if transactions and hasattr(transactions[0], "model_dump") else transactions

                for t in tx_list:
                    if t.get("tx_code") != "931":
                        continue

                    tx_narrative = (t.get("tx_narrative") or "").lower()
                    src = (t.get("src") or "").strip().upper()

                    if not ("gp" in tx_narrative or src == "K"):
                        continue

                    result["transacted_outside_safe_countries"] = True
                    country = t.get("country_of_origin")
                    if country and country in country_risk_map:
                        category = country_risk_map[country]
                        credit_eur = t.get("credit_eur")
                        if credit_eur is not None:
                            result[category].setdefault(country, []).append(float(credit_eur))

            # Calculate percentages from svoc turnover
            total_turnover = sum(
                float(s.turnover_selected or 0)
                for s in (state.active_svoc_data or [])
                if hasattr(s, "turnover_selected") and s.turnover_selected
            )

            def _percentages(country_dict: dict) -> dict:
                if total_turnover <= 0:
                    return {c: 0.0 for c in country_dict}
                return {
                    c: round((sum(amounts) / total_turnover) * 100, 2)
                    for c, amounts in country_dict.items()
                }

            hr_pct = _percentages(result["high_risk_countries"])
            vhr_pct = _percentages(result["very_high_risk_countries"])

            result["high_risk_countries_percentages"] = hr_pct
            result["very_high_risk_countries_percentages"] = vhr_pct
            result["high_risk_total_percentage"] = round(sum(hr_pct.values()), 2)
            result["very_high_risk_total_percentage"] = round(sum(vhr_pct.values()), 2)

            # Store in state
            state.country_risk_analysis = result
            state.mark_step("analyze_country_risk")

            logger.info(
                f"Country risk done — outside_safe: {result['transacted_outside_safe_countries']}, "
                f"high_risk: {len(result['high_risk_countries'])}, "
                f"very_high: {len(result['very_high_risk_countries'])}, "
                f"prohibited: {len(result['prohibited_countries'])}"
            )
            return result

        try:
            result = asyncio.run(_analyze())
            return json.dumps(result, default=str)
        except Exception as exc:
            logger.error(f"analyze_country_risk failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})

    @tool
    def analyze_suspicious_activity(party_id: str) -> str:
        """
        Analyze transaction history for suspicious activity across all active bundles.
        Calls an internal LLM agent per bundle to detect red flags.
        Saves results directly to state.
        """
        async def _analyze():
            if not state.active_servicelink_bundles:
                return {"error": "No active bundles. Run filter_active_accounts first.", "status": "failed"}

            prompt_template = await state.db.agent.get_agent_prompt(7.0)
            if not prompt_template:
                return {"error": "Suspicious activity prompt not found in database.", "status": "failed"}

            account_summaries = []
            all_anomalies = []
            suspicious_detected = False

            for bundle in state.active_servicelink_bundles:
                if not bundle.account_details or not bundle.transactions:
                    continue

                transaction_list = [t.model_dump() for t in bundle.transactions]
                account_no = bundle.transactions[0].account_no

                prompt = prompt_template.format(
                    account_no=account_no,
                    transactions=json.dumps(transaction_list, indent=2, default=str),
                )

                analysis_agent = Agent(
                    system_prompt="""You are a financial crime analyst.
                    Analyze the provided transactions and return ONLY a valid JSON object.
                    No explanation. No markdown. No code blocks. Raw JSON only.""",
                    model=get_model(),
                )

                try:
                    response = str(analysis_agent(prompt))
                    response = response.strip().strip("```json").strip("```").strip()
                    result = json.loads(response)

                    is_suspicious = result.get("suspicious_activity_detected", False)
                    red_flags = result.get("red_flags", [])

                    if is_suspicious:
                        suspicious_detected = True
                        all_anomalies.extend(red_flags)

                    account_summaries.append({
                        "account_no": account_no,
                        "nsc": bundle.transactions[0].nsc,
                        "transaction_count": len(bundle.transactions),
                        "suspicious_activity_detected": is_suspicious,
                        "red_flags": red_flags,
                        "overall_assessment": result.get("overall_assessment", ""),
                    })
                    logger.info(f"Suspicious activity analyzed for account: {account_no}")

                except (json.JSONDecodeError, Exception) as exc:
                    logger.error(f"Suspicious activity analysis failed for {account_no}: {exc}")
                    account_summaries.append({
                        "account_no": account_no,
                        "nsc": bundle.transactions[0].nsc,
                        "transaction_count": len(bundle.transactions),
                        "suspicious_activity_detected": False,
                        "red_flags": [],
                        "overall_assessment": f"Analysis failed: {exc}",
                    })

            # Save directly to state
            state.suspicious_activity_results = account_summaries
            state.suspicious_activity_detected = suspicious_detected
            state.mark_step("analyze_suspicious_activity")

            logger.info(
                f"Suspicious activity complete — "
                f"detected: {suspicious_detected}, anomalies: {len(all_anomalies)}"
            )
            return {
                "status": "ok",
                "accounts_analyzed": len(account_summaries),
                "suspicious_activity_detected": suspicious_detected,
                "anomalies_count": len(all_anomalies),
            }

        try:
            result = asyncio.run(_analyze())
            return json.dumps(result, default=str)
        except Exception as exc:
            logger.error(f"analyze_suspicious_activity failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})

    @tool
    def calculate_cash_percentage(party_id: str) -> str:
        """
        Calculate the average cash percentage across all active SVoC accounts.
        Must be called after filter_active_accounts.
        """
        if not state.active_svoc_data:
            return json.dumps({"error": "No active SVoC data. Run filter_active_accounts first.", "status": "failed"})

        total = sum((s.cash_percentage or 0) for s in state.active_svoc_data)
        avg = round((total / len(state.active_svoc_data)) * 100, 4)

        state.final_cash_percentage = avg
        state.mark_step("calculate_cash_percentage")

        logger.info(f"Cash percentage: {avg}%")
        return json.dumps({"cash_percentage": avg, "status": "ok"})

    @tool
    def create_am_summary(party_id: str) -> str:
        """
        Create a human-readable summary of all activity monitor analysis for the party.
        Must be called after all other tools have run.
        """
        summary_parts = []

        if state.suspicious_activity_results:
            suspicious_accounts = [a for a in state.suspicious_activity_results if a.get("suspicious_activity_detected")]
            summary_parts.append(f"Analyzed {len(state.suspicious_activity_results)} accounts, with {len(suspicious_accounts)} showing suspicious activity.")

        if state.employment_analysis_results:
            employed = [e for e in state.employment_analysis_results if e.get("employment_status") == "employed"]
            summary_parts.append(f"Employment analysis suggests {len(employed)} accounts are associated with employed individuals.")

        if state.country_risk_analysis and state.country_risk_analysis.get("transacted_outside_safe_countries"):
            high_risk = state.country_risk_analysis.get("high_risk_countries", {})
            vhr = state.country_risk_analysis.get("very_high_risk_countries", {})
            summary_parts.append(f"Country risk analysis detected transactions involving {len(high_risk)} high-risk and {len(vhr)} very high-risk countries.")

        return json.dumps({"summary": " ".join(summary_parts), "status": "ok"})

    return [
        filter_active_accounts,
        analyze_employment,
        analyze_country_risk,
        analyze_suspicious_activity,
        calculate_cash_percentage,
        create_am_summary,
    ]