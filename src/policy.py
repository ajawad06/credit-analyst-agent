"""
Credit Analyst Agent — Policy Rule Gate

Hard-violation rules that auto-decline a case before it reaches
either the fine-tuned model or the commercial rule.
"""


def check_hard_policy_violations(applicant, bureau, dti):
    if bureau["existing_defaults"] >= 2:
        return "Auto-decline: 2+ existing defaults on file (hard policy rule)."
    if dti != float("inf") and dti > 65:
        return f"Auto-decline: DTI of {dti}% exceeds maximum allowable threshold (65%)."
    if bureau["credit_score"] < 500:
        return f"Auto-decline: credit score {bureau['credit_score']} below minimum floor (500)."
    return None