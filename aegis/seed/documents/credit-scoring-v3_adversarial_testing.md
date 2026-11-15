# MOCK DATA — Adversarial Testing Report: Credit Scoring Model v3

**Last updated:** 2026-09-15

## Attack scenarios

| Scenario | Type | Tested |
|---|---|---|
| Feature perturbation (income inflation) | Evasion | Yes |
| Label poisoning via synthetic fraudulent data | Poisoning | Yes |
| Model inversion to infer training data | Inversion | Yes |
| Feature importance manipulation | Adversarial example | Yes |

## Results

All four attack scenarios were tested on a held-out adversarial test set.

- Feature perturbation: model robustness score 0.91 (threshold 0.85) — PASS
- Label poisoning: model accuracy degraded by < 2% under 5% label noise — PASS
- Model inversion: no training records recoverable within 1,000 queries — PASS
- Feature importance manipulation: decision boundaries stable under FGSM attack — PASS

## Mitigations implemented

- Input validation layer rejecting out-of-distribution feature values.
- Differential privacy noise added to training gradients (ε=1.0).
- Rate limiting on the inference API to prevent bulk extraction attacks.
