# MOCK DATA — Model Card: Resume Screener v2

**Last updated:** 2026-09-01
**Owner:** talent-team@example.com
**Risk tier:** High
**Version:** 2.0.1

## Model details

Binary classification model that ranks job applicants based on resume embeddings.
Outputs a hire/no-hire recommendation. Threshold set at score >= 0.50.

## Intended use

Shortlisting applicants for initial screening calls. Final hiring decision is
always made by a human recruiter.

## Training data

Internal HR database, 2020–2025. 50,000 historical applications.

## Known limitations

- Trained on historical decisions which may reflect prior human bias.
- Not validated for roles outside engineering and operations.

## Fairness evaluation

<!-- required_sections: ["Fairness evaluation"] -->

Last bias audit: **MISSING** — no completed bias review on record.
