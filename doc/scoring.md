# Scoring

This document covers the complete Aegis Index formula, severity weights, RAG bands, maturity levels, and org roll-up rules.

---

## Aegis Index formula

```
pillar score = 100 × Σ(status_points × severity_weight) / Σ(severity_weight)

system Aegis Index = average of all pillar scores that have at least one scored result

org Aegis Index = weighted average of system indices, weighted by risk tier
```

`na` and `pending` results are excluded from both numerator and denominator.

---

## Status points

| Status | Points |
|---|---|
| `pass` | 1.0 |
| `warn` | 0.5 |
| `fail` | 0.0 |
| `error` | 0.0 |
| `na` | excluded |
| `pending` | excluded |

---

## Severity weights

| Severity | Weight |
|---|---|
| `critical` | 4 |
| `high` | 3 |
| `medium` | 2 |
| `low` | 1 |

---

## Worked example

A system has 4 test results in its Fairness pillar:

| Test | Severity | Status | Points | Weight | Contribution |
|---|---|---|---|---|---|
| FAIR-001 | critical | fail | 0.0 | 4 | 0.0 |
| FAIR-002 | high | pass | 1.0 | 3 | 3.0 |
| FAIR-003 | high | warn | 0.5 | 3 | 1.5 |
| FAIR-004 | medium | pass | 1.0 | 2 | 2.0 |

```
Σ(contribution) = 0.0 + 3.0 + 1.5 + 2.0 = 6.5
Σ(weight)       = 4 + 3 + 3 + 2        = 12

Fairness pillar score = 100 × 6.5 / 12 = 54.2
```

Since FAIR-001 is a **critical fail**, the RAG for this pillar is **Red** regardless of the numeric score.

---

## RAG bands

| RAG | Condition |
|---|---|
| **Green** | score ≥ 80 AND no critical failures |
| **Amber** | score ≥ 60 AND no critical failures |
| **Red** | score < 60 OR any critical failure |

The critical failure override is absolute: a system with Aegis Index 95.0 that has one `critical` `fail` result is **Red**.

---

## Maturity levels

| Level | Label | Score range |
|---|---|---|
| 1 | Initial | < 20 |
| 2 | Repeatable | 20–39 |
| 3 | Defined | 40–59 |
| 4 | Managed | 60–79 |
| 5 | Optimised | ≥ 80 |

Maturity is derived from the system's overall Aegis Index using these bands.

---

## BU and org roll-up

Business unit score: simple average of all system scores within the BU.

Org score: weighted average of system scores, with weights based on risk tier:

| Risk tier | Weight |
|---|---|
| `unacceptable` | 4 |
| `high` | 3 |
| `limited` | 2 |
| `minimal` | 1 |

Org RAG applies the same bands: Green ≥ 80 and no critical fail, Amber 60–79 and no critical fail, Red otherwise. A single critical failure anywhere in the org makes the org RAG Red.

---

## Pillar scores

Each of the 9 pillars is scored independently using the formula above. Only pillars that have at least one scored (non-`na`, non-`pending`) result for a system appear in that system's breakdown. The system Aegis Index is the unweighted average of its pillar scores (all pillars weighted equally at the system level; severity within a pillar weights individual tests).

---

## Configuration

All weights, thresholds, and band boundaries live in `aegis/scoring/config.yaml`. Nothing is hardcoded in the scoring engine. To adjust severity weights or RAG boundaries, edit that file and re-run `aegis score`.

```yaml
# excerpt from scoring/config.yaml
severity_weights:
  critical: 4
  high: 3
  medium: 2
  low: 1

rag_bands:
  green_min: 80
  amber_min: 60

maturity_bands:
  - { max: 20,  level: 1, label: Initial }
  - { max: 40,  level: 2, label: Repeatable }
  - { max: 60,  level: 3, label: Defined }
  - { max: 80,  level: 4, label: Managed }
  - { max: 101, level: 5, label: Optimised }
```
