# Credit Analyst Agent

An agent built for "replacing" Credit Analyst role in a bank, wrapping a fine-tuned
loan-risk classifier inside a multi-step LangChain agent for a real banking use case.

## Use case

The agent automates the role of a **credit analyst** at a bank. A credit
analyst reviews loan applications, calculates financial ratios (DTI, DSCR,
LTV), pulls credit bureau data, assesses collateral, flags red flags
(inconsistent documentation, existing defaults, high debt load), and produces
a structured recommendation: approve, decline, or refer; backed by
reasoning. This role was chosen because its output is already a structured,
rule-and-judgment-driven decision, making it a natural fit for an agent that
combines deterministic checks with model-based judgment.

## Architecture

The agent runs a fixed 5-step pipeline, built with LangChain's Expression
Language (LCEL):

1. **Intake & validation** - parse the applicant's details (income, debts,
   loan amount/purpose, collateral, employment history, etc.)
2. **Mock tool calls** - calculate DTI, DSCR, and LTV, and pull mock credit
   bureau data (score, band, late payments, existing defaults)
3. **Policy rule gate** - hard-violation rules (2+ existing defaults, DTI
   over 65%, credit score under 500) that auto-decline a case before any
   further judgment step runs
4. **Judgment step** - either:
   - the **fine-tuned model**, for retail (personal-income) applicants, or
   - a **deterministic commercial rule**, for commercial (DSCR-driven)
     applicants (see Limitations below for why)
5. **Branch on decision** - approve auto-proceeds to disbursement, decline
   auto-rejects with reasoning attached, refer escalates to a human
   underwriter

Output is a structured `CreditMemo`: decision, decision source, ratios,
credit score/band, red flags, reasoning, and next action.

## Limitations

- **The fine-tuned model was trained exclusively on retail/personal-income
  loan profiles.** Commercial applicants (evaluated via DSCR, with no
  personal monthly income) are out-of-distribution for it. Testing
  confirmed this: even profile-text adjustments (correcting income framing,
  omitting inapplicable DTI values) didn't fix it — the model produced
  incoherent, sometimes self-contradictory reasoning on clean commercial
  cases with strong fundamentals. Since the gap is in the model's training
  data rather than the prompt, no amount of formatting was going to close
  it in this timeframe.
- **Resulting design decision:** commercial applicants are routed to a
  separate, transparent, deterministic rule (`commercial_rule_tool`)
  instead of the fine-tuned model. It auto-declines on DSCR < 1.0,
  auto-approves on strong DSCR + credit + clean history, and refers
  everything else to a human underwriter. This is a conscious scope
  boundary, not a bug — the agent knows what it doesn't know and hands
  off accordingly.
- **The real fix** would be a second fine-tuning pass on a labeled
  commercial-loan dataset (DSCR, LTV, business credit history →
  approve/decline/refer), following the same process as Assignment 1.
  This is out of scope for the current timeline but is the clear next step.
- All bureau/ratio data is mocked; no real banking systems are integrated.
- The policy gate, commercial rule, and model judgment are evaluated in a
  fixed order per applicant — there is no multi-turn conversation or
  ability to request additional information mid-review in this version.

## Demo

See [`demo/example_runs.md`](demo/example_runs.md) for 5 end-to-end test
cases covering all three decision sources (`policy_rule`,
`commercial_rule`, `model_judgment`) across both retail and commercial
loan types.

## Repo structure

```
credit-analyst-agent/
├── README.md
├── requirements.txt
├── notebooks/
│   └── credit_analyst_agent.ipynb   # fine-tuning + full agent build, runnable end to end
├── src/
│   ├── tools.py     # Applicant schema, DTI/DSCR/LTV calculators, mock bureau pull
│   ├── policy.py    # hard policy-violation rules
│   ├── model.py     # profile-text builder, fine-tuned model call, decision parsing
│   └── agent.py     # LangChain tools, commercial rule, LCEL chain, review_applicant()
└── demo/
    └── example_runs.md   # 5 end-to-end demo cases with applicant input + agent output
```

## How to run

The agent requires a GPU to run the fine-tuned model efficiently. The
notebook in `notebooks/` is the runnable entry point (developed and tested
on Kaggle, T4 GPU): it includes the fine-tuning section, the pre-LangChain
building blocks, the LangChain orchestration layer, and the demo cell.
The `src/` files mirror the same code in a more structured, non-notebook
form for readability.

`model_judgment_tool` in `src/agent.py` expects `model` and `tokenizer` to
already be loaded in scope (as they are in the notebook session) -  the
file is not meant to run standalone without that model loaded first.
