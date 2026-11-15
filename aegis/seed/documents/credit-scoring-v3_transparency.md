# MOCK DATA — Transparency Documentation: Credit Scoring Model v3

**Last updated:** 2026-10-01

## How decisions are explained

Applicants receive a decision letter that includes:
1. The outcome (approved / referred / declined).
2. The top 3 factors that most influenced the decision (e.g. "Payment history",
   "Debt-to-income ratio", "Length of credit history").
3. If declined, the primary reason and steps the applicant can take to improve.

SHAP values are computed at inference time and mapped to plain-language labels
by the Risk team. All explanations are reviewed by a credit officer before dispatch.

## How to request a review

Applicants may request a human review of any decision within 30 days by
contacting credit-review@example.com or calling the helpline.
