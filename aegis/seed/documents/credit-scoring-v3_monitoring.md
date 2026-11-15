# MOCK DATA — Model Monitoring Dashboard: Credit Scoring Model v3

**Last updated:** 2026-11-01

## Metrics tracked

| Metric | Current | Threshold | Status |
|---|---|---|---|
| Approval rate (7-day rolling) | 68% | 60-80% | OK |
| Score distribution PSI | 0.04 | < 0.10 | OK |
| Input feature drift (income) | 0.02 | < 0.05 | OK |
| Disparate impact ratio (income band) | 0.86 | >= 0.80 | OK |
| Default rate (90-day lag) | 3.2% | < 5% | OK |
| API p99 latency | 42ms | < 200ms | OK |

## Alerting

Alerts fire to risk-team@example.com and PagerDuty when:
- PSI > 0.10 (data drift)
- Disparate impact < 0.80 (fairness alert)
- Default rate > 5% (business alert)

## Last reviewed

Risk & Compliance AI Team — 2026-11-01
