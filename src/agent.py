"""
Credit Analyst Agent — LangChain Orchestration Layer

Wraps the pre-LangChain building blocks as LangChain @tool components
and orchestrates them with an LCEL chain ending in a RunnableBranch
for the approve / decline / refer decision.
"""

from typing import Optional, Literal
from dataclasses import dataclass, asdict

from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.runnables import RunnableLambda, RunnableBranch

from tools import Applicant, calc_dti, calc_dscr, calc_ltv, mock_credit_bureau_pull
from policy import check_hard_policy_violations
from model import call_v6, build_profile_text


class ApplicantSchema(BaseModel):
    name: str
    monthly_income: float
    monthly_debt_payments: float
    requested_loan_amount: float
    loan_purpose: str
    collateral_value: Optional[float] = None
    annual_net_operating_income: Optional[float] = None
    annual_debt_service: Optional[float] = None
    employment_years: float = 0.0
    late_payments_last_2y: int = 0
    existing_defaults: int = 0


def _to_applicant(a: ApplicantSchema) -> Applicant:
    return Applicant(**a.model_dump())


@tool("calc_dti_tool", args_schema=ApplicantSchema)
def calc_dti_tool(**kwargs) -> float:
    """Calculate the applicant's Debt-to-Income (DTI) ratio as a percentage."""
    return calc_dti(_to_applicant(ApplicantSchema(**kwargs)))


@tool("calc_dscr_tool", args_schema=ApplicantSchema)
def calc_dscr_tool(**kwargs) -> Optional[float]:
    """Calculate Debt Service Coverage Ratio (DSCR) for commercial loan applicants."""
    return calc_dscr(_to_applicant(ApplicantSchema(**kwargs)))


@tool("calc_ltv_tool", args_schema=ApplicantSchema)
def calc_ltv_tool(**kwargs) -> Optional[float]:
    """Calculate Loan-to-Value (LTV) ratio as a percentage when collateral exists."""
    return calc_ltv(_to_applicant(ApplicantSchema(**kwargs)))


@tool("credit_bureau_tool", args_schema=ApplicantSchema)
def credit_bureau_tool(**kwargs) -> dict:
    """Pull (mock) credit bureau data: score, band, late payments, existing defaults."""
    return mock_credit_bureau_pull(_to_applicant(ApplicantSchema(**kwargs)))


class PolicyGateInput(BaseModel):
    dti: float
    bureau: dict = Field(description="Output of credit_bureau_tool")


@tool("policy_gate_tool", args_schema=PolicyGateInput)
def policy_gate_tool(dti: float, bureau: dict) -> Optional[str]:
    """Check hard policy-violation rules (defaults, DTI ceiling, credit floor).
    Returns a decline reason string if violated, else None."""
    return check_hard_policy_violations(None, bureau, dti)


class ModelJudgmentInput(BaseModel):
    profile_text: str


@tool("model_judgment_tool", args_schema=ModelJudgmentInput)
def model_judgment_tool(profile_text: str) -> dict:
    """Call the fine-tuned v6 checkpoint on a profile and return decision + reasoning.
    NOTE: `model` and `tokenizer` are expected to be in scope (loaded in the
    notebook session) — this file is not runnable standalone without them."""
    verdict = call_v6(profile_text, model=model, tokenizer=tokenizer)
    return {"decision": verdict.decision, "reasoning": verdict.reasoning}


class CommercialRuleInput(BaseModel):
    dscr: float
    credit_score: int
    existing_defaults: int
    late_payments_last_2y: int


@tool("commercial_rule_tool", args_schema=CommercialRuleInput)
def commercial_rule_tool(dscr: float, credit_score: int, existing_defaults: int,
                          late_payments_last_2y: int) -> dict:
    """Deterministic underwriting rule for commercial/DSCR-driven applicants,
    used in place of v6 (which was never fine-tuned on commercial profiles)."""
    if dscr < 1.0:
        return {"decision": "decline",
                "reasoning": f"DSCR of {dscr} is below 1.0 — income does not "
                              f"cover debt service. Deterministic commercial rule."}
    if dscr >= 1.5 and credit_score >= 700 and existing_defaults == 0 and late_payments_last_2y == 0:
        return {"decision": "approve",
                "reasoning": f"DSCR of {dscr}, credit score {credit_score}, "
                              f"clean payment history. Deterministic commercial rule."}
    return {"decision": "refer",
            "reasoning": f"DSCR of {dscr} and credit score {credit_score} don't "
                          f"meet the clear-approve or clear-decline thresholds — "
                          f"needs human underwriter judgment. Deterministic commercial rule."}


TOOLS = [calc_dti_tool, calc_dscr_tool, calc_ltv_tool, credit_bureau_tool,
         policy_gate_tool, model_judgment_tool, commercial_rule_tool]


@dataclass
class CreditMemo:
    applicant_name: str
    decision: Literal["approve", "decline", "refer"]
    decision_source: Literal["policy_rule", "commercial_rule", "v6_model"]
    reasoning: str
    dti: float
    dscr: Optional[float]
    ltv: Optional[float]
    credit_score: int
    credit_band: str
    red_flags: list
    next_action: str

    def as_text(self) -> str:
        flags = "\n".join(f"  - {f}" for f in self.red_flags) if self.red_flags else "  - none"
        dscr_line = f"\n  DSCR: {self.dscr}" if self.dscr is not None else ""
        ltv_line = f"\n  LTV:  {self.ltv}%" if self.ltv is not None else ""
        dti_display = "N/A (commercial)" if self.dti == float("inf") else f"{self.dti}%"
        return (
            f"{'='*60}\n"
            f"CREDIT MEMO — {self.applicant_name}\n"
            f"{'='*60}\n"
            f"DECISION: {self.decision.upper()}  (source: {self.decision_source})\n\n"
            f"Ratios:\n"
            f"  DTI:  {dti_display}{dscr_line}{ltv_line}\n"
            f"  Credit score: {self.credit_score} ({self.credit_band})\n\n"
            f"Red flags:\n{flags}\n\n"
            f"Reasoning:\n  {self.reasoning}\n\n"
            f"Next action: {self.next_action}\n"
        )


def _red_flags(applicant: Applicant, bureau: dict, dti: float, ltv: Optional[float]) -> list:
    flags = []
    if bureau["existing_defaults"] > 0:
        flags.append(f"{bureau['existing_defaults']} existing default(s) on record")
    if bureau["late_payments_last_2y"] >= 3:
        flags.append(f"{bureau['late_payments_last_2y']} late payments in the last 2 years")
    if dti != float("inf") and dti > 45:
        flags.append(f"elevated DTI ({dti}%)")
    if ltv is not None and ltv > 90:
        flags.append(f"high LTV ({ltv}%) — thin collateral cushion")
    if applicant.employment_years < 1:
        flags.append("under 1 year employment history")
    return flags


def _intake(applicant: Applicant) -> dict:
    """Step 1: intake + step 2: run all tools."""
    a_dict = asdict(applicant)
    dti = calc_dti_tool.invoke(a_dict)
    dscr = calc_dscr_tool.invoke(a_dict)
    ltv = calc_ltv_tool.invoke(a_dict)
    bureau = credit_bureau_tool.invoke(a_dict)
    red_flags = _red_flags(applicant, bureau, dti, ltv)
    return {
        "applicant": applicant,
        "dti": dti, "dscr": dscr, "ltv": ltv,
        "bureau": bureau, "red_flags": red_flags,
    }


def _policy_and_judgment(state: dict) -> dict:
    """Step 3: policy gate. Step 3b: commercial rule (bypasses v6). Step 4: v6 judgment."""
    decline_reason = policy_gate_tool.invoke({"dti": state["dti"], "bureau": state["bureau"]})
    if decline_reason:
        state["decision"] = "decline"
        state["decision_source"] = "policy_rule"
        state["reasoning"] = decline_reason
        return state

    if state["applicant"].monthly_income == 0 and state["dscr"] is not None:
        verdict = commercial_rule_tool.invoke({
            "dscr": state["dscr"],
            "credit_score": state["bureau"]["credit_score"],
            "existing_defaults": state["bureau"]["existing_defaults"],
            "late_payments_last_2y": state["bureau"]["late_payments_last_2y"],
        })
        state["decision"] = verdict["decision"]
        state["decision_source"] = "commercial_rule"
        state["reasoning"] = verdict["reasoning"]
        return state

    profile_text = build_profile_text(state["applicant"], state["bureau"],
                                       state["dti"], state["dscr"], state["ltv"])
    verdict = model_judgment_tool.invoke({"profile_text": profile_text})
    state["decision"] = verdict["decision"]
    state["decision_source"] = "v6_model"
    state["reasoning"] = verdict["reasoning"]
    return state


def _handle_approve(state: dict) -> dict:
    state["next_action"] = "Auto-proceed: loan approved, forward to disbursement workflow."
    return state


def _handle_decline(state: dict) -> dict:
    state["next_action"] = "Auto-reject: applicant notified with reasoning; case closed."
    return state


def _handle_refer(state: dict) -> dict:
    state["next_action"] = "Escalated: routed to human underwriter for manual review."
    return state


_decision_branch = RunnableBranch(
    (lambda s: s["decision"] == "approve", RunnableLambda(_handle_approve)),
    (lambda s: s["decision"] == "decline", RunnableLambda(_handle_decline)),
    RunnableLambda(_handle_refer),  # default: refer
)


def _to_memo(state: dict) -> CreditMemo:
    return CreditMemo(
        applicant_name=state["applicant"].name,
        decision=state["decision"],
        decision_source=state["decision_source"],
        reasoning=state["reasoning"],
        dti=state["dti"], dscr=state["dscr"], ltv=state["ltv"],
        credit_score=state["bureau"]["credit_score"],
        credit_band=state["bureau"]["band"],
        red_flags=state["red_flags"],
        next_action=state["next_action"],
    )


credit_analyst_chain = (
    RunnableLambda(_intake)
    | RunnableLambda(_policy_and_judgment)
    | _decision_branch
    | RunnableLambda(_to_memo)
)


def review_applicant(applicant: Applicant) -> CreditMemo:
    """Public entry point: run the full 5-step agent on one applicant."""
    return credit_analyst_chain.invoke(applicant)