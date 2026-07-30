# Demo — Credit Analyst Agent End-to-End Runs

Five applicants covering all three decision sources across both loan types.

## 1. Tariq Textiles — commercial, strong DSCR
Clean commercial approve: DSCR 1.67, excellent credit, no defaults/late payments.
Handled by the deterministic `commercial_rule`, since v6 was never fine-tuned on
commercial/DSCR-driven profiles.

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

## 2. Saima — retail, high but sub-ceiling DTI
Genuine borderline case handled by the fine-tuned model (`v6_model`): high income
offset by high DTI, referred for underwriting judgment on affordability.

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

## 3. Waseem Traders — commercial, real policy violation
Shows the hard policy gate (`policy_rule`) catching a genuine violation — 2 existing
defaults — before either the commercial rule or v6 ever runs, confirming the gate
applies regardless of loan type.

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

## 4. Zara Foods — commercial, weak DSCR
DSCR below 1.0 (income doesn't cover debt service) → auto-decline via
`commercial_rule`.

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

## 5. Naveed — retail, real high DTI
Genuine DTI of 80%, above the 65% ceiling → auto-decline via `policy_rule`.

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