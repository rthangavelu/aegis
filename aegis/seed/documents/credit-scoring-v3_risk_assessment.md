# MOCK DATA — AI Risk Assessment: Credit Scoring Model v3

**Last updated:** 2026-09-01

## Risk identification

| Risk ID | Description | Category |
|---|---|---|
| RISK-001 | Discriminatory lending decisions | Fairness |
| RISK-002 | Model drift leading to increased defaults | Reliability |
| RISK-003 | Adversarial manipulation of credit scores | Safety |
| RISK-004 | PII leakage from training data | Privacy |
| RISK-005 | Regulatory non-compliance (EU AI Act Art. 10) | Compliance |

## Impact assessment

| Risk ID | Likelihood | Impact | Score | Mitigation |
|---|---|---|---|---|
| RISK-001 | Medium | Critical | 12 | Fairlearn constraints, quarterly bias audits |
| RISK-002 | Medium | High | 9 | Monitoring dashboard, drift alerts |
| RISK-003 | Low | High | 6 | Adversarial robustness testing, rate limiting |
| RISK-004 | Low | Critical | 8 | Differential privacy, data minimization |
| RISK-005 | Low | High | 6 | Regulatory mapping, legal review |

## Residual risk

All residual risks assessed as ACCEPTABLE by Risk Officer on 2026-09-01.
Next review scheduled: 2027-03-01.
