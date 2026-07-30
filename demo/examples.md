# Demo - Credit Analyst Agent End-to-End Runs

Five applicants covering all three decision sources across both loan types.
Each case shows the applicant input, then the agent's output memo.

## 1. Tariq Textiles: commercial loan, strong DSCR
Clean commercial approve: DSCR 1.67, excellent credit, no defaults/late payments.
Handled by the deterministic `commercial_rule`, since v6 was never fine-tuned on
commercial/DSCR-driven profiles.

**Applicant input:**
```
name: Tariq Textiles v2 (strong DSCR commercial, retest)
monthly_income: 0
monthly_debt_payments: 0
requested_loan_amount: 5,000,000
loan_purpose: working capital
collateral_value: None
annual_net_operating_income: 3,000,000
annual_debt_service: 1,800,000
employment_years: 12
late_payments_last_2y: 0
existing_defaults: 0
```

**Agent output:**
```
============================================================
CREDIT MEMO — Tariq Textiles v2 (strong DSCR commercial, retest)
============================================================
DECISION: APPROVE  (source: commercial_rule)

Ratios:
  DTI:  N/A (commercial)
  DSCR: 1.67
  Credit score: 750 (excellent)

Red flags:
  - none

Reasoning:
  DSCR of 1.67, credit score 750, clean payment history. Deterministic commercial rule.

Next action: Auto-proceed: loan approved, forward to disbursement workflow.
```

## 2. Saima - retail loan, high but sub-ceiling DTI
Genuine borderline case handled by the fine-tuned model (`v6_model`): high income
offset by high DTI, referred for underwriting judgment on affordability.

**Applicant input:**
```
name: Saima (retail, high but sub-ceiling DTI)
monthly_income: 80,000
monthly_debt_payments: 48,000
requested_loan_amount: 300,000
loan_purpose: home renovation
collateral_value: 350,000
employment_years: 6
late_payments_last_2y: 0
existing_defaults: 0
```

**Agent output:**
```
============================================================
CREDIT MEMO — Saima (retail, high but sub-ceiling DTI)
============================================================
DECISION: REFER  (source: v6_model)

Ratios:
  DTI:  60.0%
  LTV:  85.71%
  Credit score: 738 (good)

Red flags:
  - elevated DTI (60.0%)

Reasoning:
  REFER: High income is offset by a very high DTI relative to that income, meaning the requested payment capacity is weak even though overall creditworthiness is good; refer for underwriting judgment on affordability rather than default risk alone.

Next action: Escalated: routed to human underwriter for manual review.
```

## 3. Waseem Traders - commercial loan, real policy violation
Shows the hard policy gate (`policy_rule`) catching a genuine violation — 2 existing
defaults — before either the commercial rule or v6 ever runs, confirming the gate
applies regardless of loan type.

**Applicant input:**
```
name: Waseem Traders (commercial, real policy violation)
monthly_income: 0
monthly_debt_payments: 0
requested_loan_amount: 1,200,000
loan_purpose: inventory financing
collateral_value: 900,000
annual_net_operating_income: 600,000
annual_debt_service: 500,000
employment_years: 3
late_payments_last_2y: 2
existing_defaults: 2
```

**Agent output:**
```
============================================================
CREDIT MEMO — Waseem Traders (commercial, real policy violation)
============================================================
DECISION: DECLINE  (source: policy_rule)

Ratios:
  DTI:  N/A (commercial)
  DSCR: 1.2
  LTV:  133.33%
  Credit score: 499 (poor)

Red flags:
  - 2 existing default(s) on record
  - high LTV (133.33%) — thin collateral cushion

Reasoning:
  Auto-decline: 2+ existing defaults on file (hard policy rule).

Next action: Auto-reject: applicant notified with reasoning; case closed.
```

## 4. Zara Foods - commercial loan, weak DSCR
DSCR below 1.0 (income doesn't cover debt service) → auto-decline via
`commercial_rule`.

**Applicant input:**
```
name: Zara Foods v2 (weak DSCR commercial, retest)
monthly_income: 0
monthly_debt_payments: 0
requested_loan_amount: 2,500,000
loan_purpose: equipment financing
collateral_value: 1,800,000
annual_net_operating_income: 900,000
annual_debt_service: 980,000
employment_years: 4
late_payments_last_2y: 1
existing_defaults: 0
```

**Agent output:**
```
============================================================
CREDIT MEMO — Zara Foods v2 (weak DSCR commercial, retest)
============================================================
DECISION: DECLINE  (source: commercial_rule)

Ratios:
  DTI:  N/A (commercial)
  DSCR: 0.92
  LTV:  138.89%
  Credit score: 717 (good)

Red flags:
  - high LTV (138.89%) — thin collateral cushion

Reasoning:
  DSCR of 0.92 is below 1.0 — income does not cover debt service. Deterministic commercial rule.

Next action: Auto-reject: applicant notified with reasoning; case closed.
```

## 5. Naveed - retail loan, real high DTI
Genuine DTI of 80%, above the 65% ceiling → auto-decline via `policy_rule`.

**Applicant input:**
```
name: Naveed (retail, real high DTI, should auto-decline)
monthly_income: 50,000
monthly_debt_payments: 40,000
requested_loan_amount: 200,000
loan_purpose: personal
collateral_value: None
employment_years: 3
late_payments_last_2y: 1
existing_defaults: 0
```

**Agent output:**
```
============================================================
CREDIT MEMO — Naveed (retail, real high DTI, should auto-decline)
============================================================
DECISION: DECLINE  (source: policy_rule)

Ratios:
  DTI:  80.0%
  Credit score: 714 (good)

Red flags:
  - elevated DTI (80.0%)

Reasoning:
  Auto-decline: DTI of 80.0% exceeds maximum allowable threshold (65%).

Next action: Auto-reject: applicant notified with reasoning; case closed.
```
