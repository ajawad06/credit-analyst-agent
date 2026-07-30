"""
Credit Analyst Agent — Fine-Tuned Model Interface

Profile-text builder (matches the format v6 was fine-tuned on) and the
function that calls v6 and parses its decision + reasoning.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Literal

from tools import Applicant


def build_profile_text(applicant: Applicant, bureau: dict, dti: float,
                        dscr: Optional[float], ltv: Optional[float]) -> str:
    """Must match the text format v6 was trained on."""
    is_commercial = dscr is not None and applicant.monthly_income == 0

    lines = [f"Applicant: {applicant.name}"]

    if is_commercial:
        lines.append("Applicant type: commercial (evaluated via DSCR, not personal income)")
    else:
        lines.append(f"Annual income: ${applicant.monthly_income * 12:,.0f}")

    lines += [
        f"Requested loan amount: ${applicant.requested_loan_amount:,.0f}",
        f"Loan purpose: {applicant.loan_purpose}",
        (f"Debt-to-Income (DTI) ratio: {dti}%" if dti != float("inf")
         else "Debt-to-Income (DTI): N/A (commercial loan, evaluated via DSCR)"),
    ]
    if dscr is not None:
        lines.append(f"Debt Service Coverage Ratio (DSCR): {dscr}")
    if ltv is not None:
        lines.append(f"Loan-to-Value (LTV) ratio: {ltv}%")
    lines += [
        f"Credit score: {bureau['credit_score']} ({bureau['band']})",
        f"Late payments (last 2 years): {bureau['late_payments_last_2y']}",
        f"Existing defaults: {bureau['existing_defaults']}",
        f"Employment history: {applicant.employment_years} years",
    ]
    return "\n".join(lines)


Decision = Literal["approve", "decline", "refer"]


@dataclass
class ModelVerdict:
    decision: Decision
    reasoning: str
    raw_output: str = field(repr=False, default="")


def build_chatml_prompt(profile_text: str) -> str:
    """Match this to the exact ChatML template used during v6 fine-tuning."""
    return (
        "<|im_start|>system\n"
        "You are a loan risk classifier. Given an applicant profile, respond with "
        "a decision (approve, decline, or refer) and a brief reasoning.\n"
        "<|im_end|>\n"
        f"<|im_start|>user\n{profile_text}\n<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def parse_decision(raw_output: str) -> Decision:
    match = re.search(r"\b(approve|decline|refer)\b", raw_output.lower())
    if match:
        return match.group(1)  # type: ignore
    return "refer"  # fail safe: unparseable output routes to human review


def call_v6(profile_text: str, model, tokenizer) -> ModelVerdict:
    """Calls the fine-tuned v6 checkpoint and parses its decision + reasoning."""
    prompt = build_chatml_prompt(profile_text)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    output_ids = model.generate(**inputs, max_new_tokens=200, temperature=0.1)
    raw_output = tokenizer.decode(
        output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
    )
    decision = parse_decision(raw_output)
    return ModelVerdict(decision=decision, reasoning=raw_output.strip(), raw_output=raw_output)