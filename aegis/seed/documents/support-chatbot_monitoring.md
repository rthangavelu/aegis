# MOCK DATA — Model Monitoring Dashboard: Customer Support Chatbot

**Last updated:** 2026-11-01

## Metrics tracked

| Metric | Current | Threshold | Status |
|---|---|---|---|
| Escalation rate (7-day rolling) | 12% | < 25% | OK |
| Jailbreak rate (eval suite) | 13.3% | < 15% | WARN |
| Groundedness score (eval suite) | 0.76 | >= 0.80 | WARN |
| Toxicity rate (eval suite) | 4.7% | < 5% | OK |
| PII leak rate (eval suite) | 0% | < 1% | OK |
| API p99 latency | 1.2s | < 3s | OK |

## Alerting

Alerts fire to cx-team@example.com when:
- Jailbreak rate > 15% (safety alert)
- Escalation rate > 25% (CX alert)
- Groundedness < 0.70 (quality alert)

## Last reviewed

Customer Experience AI Team — 2026-11-01
