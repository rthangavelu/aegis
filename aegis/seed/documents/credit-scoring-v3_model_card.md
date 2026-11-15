# MOCK DATA — Model Card: Credit Scoring Model v3

**Last updated:** 2026-10-01
**Owner:** risk-team@example.com
**Risk tier:** High
**Version:** 3.0.0

## Model details

Gradient-boosted classification model predicting 12-month default probability
for personal loan applicants. Output is a continuous score 0–1; threshold 0.50.

## Intended use

Setting credit limits and interest rate tiers for new personal loan applications.
All decisions above $50,000 require human review before communication.

## Training data

Credit bureau data and internal account history, 2015–2025. 2M records.
EU General Data Protection Regulation (GDPR) compliant data processing agreement in place.

## Fairness evaluation

Disparate impact ratio (income band): 0.86 — passes four-fifths rule.
Last bias audit: 2026-10-01 (ML Lead).

## Known limitations

Model performance degrades on applicants with fewer than 24 months of credit
history. Not validated for use outside the UK and Ireland jurisdictions.

## Regulatory mapping

- EU AI Act Art. 10, 13, 14 (high-risk system)
- NIST AI RMF GOVERN 1.1, MANAGE 2.2, MEASURE 2.11
