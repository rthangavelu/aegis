# Explainability Documentation — Credit Scoring v3
<!-- mock: true -->

**System:** credit-scoring-v3  
**Document date:** 2026-01-15  
**Author:** ML Lead  
**Next review:** 2027-01-15

---

## Explanation method

The credit scoring model uses **SHAP (SHapley Additive exPlanations)** with a `TreeExplainer` for global feature importance and local instance-level explanations. SHAP was chosen because:

- The underlying model is a gradient-boosted tree (XGBoost / scikit-learn GradientBoostingClassifier), which TreeExplainer handles exactly (no kernel approximation needed).
- SHAP values satisfy desirable properties: local accuracy, missingness, and consistency.
- Explanations can be presented to affected individuals as "the top factors that influenced your credit decision", satisfying the GDPR Art. 22 right to explanation.

**Implementation:** `aegis/engine/checks/explainability.py` — `ShapTreeExplainer` class. The explainer is fitted once per model version and cached. Each inference call returns a SHAP value vector alongside the prediction.

---

## Method evaluation

| Property | Measure | Result |
|----------|---------|--------|
| Faithfulness | Sufficiency score (top-3 features vs. full model) | 0.91 — top 3 features account for 91% of prediction variance |
| Stability | Std. dev. of SHAP values across 10 runs on same instance | < 0.001 (TreeExplainer is deterministic) |
| Human intelligibility | Domain expert rating (5 raters, 1-5 scale, 10 cases) | Mean 4.2 / 5.0 |
| Completeness | Fraction of prediction explained by provided features | 1.0 (by SHAP construction) |

The TreeExplainer is deterministic given a fixed model and input, so stability is perfect. The faithfulness metric confirms that credit score, income and loan amount dominate the model's decisions.

---

## Example explanations

**Example 1 — Approved (label=1, prediction=1)**  
Input: income=52000, credit_score=720, loan_amount=15000, age=34, gender=M  
SHAP contributions: credit_score +0.42, income +0.31, loan_amount -0.08, age +0.02, gender 0.00  
Plain language: "Your application was approved. The main positive factors were your credit score (720) and income (£52,000). The loan amount requested slightly reduced the score."

**Example 2 — Declined (label=0, prediction=0)**  
Input: income=18000, credit_score=560, loan_amount=20000, age=28, gender=F  
SHAP contributions: credit_score -0.38, income -0.29, loan_amount -0.14, age +0.03, gender 0.00  
Plain language: "Your application was declined. The main factors were your credit score (560) and income (£18,000), which were below the thresholds required for the requested loan amount."

**Example 3 — Borderline (label=1, prediction=1, low confidence)**  
Input: income=27000, credit_score=615, loan_amount=10000, age=45, gender=M  
SHAP contributions: credit_score +0.11, income +0.09, loan_amount -0.04, age +0.01, gender 0.00  
Plain language: "Your application was approved. Your credit score and income both meet the minimum thresholds. This was a borderline decision — a small change in either factor could have changed the outcome."

---

## Limitations

1. **SHAP does not capture interaction effects well in high-cardinality feature spaces.** The current feature set is small (5 features), so this is not a concern, but retraining on a richer feature set may require TreeShap interaction values to be meaningful.
2. **Global explanations assume feature independence.** The income-gender correlation in the seed data means global SHAP values partially conflate gender and income effects. The local (per-instance) explanations are correct but should not be averaged into a gender-based global importance.
3. **Recourse explanations are not yet implemented.** SHAP tells the individual what drove the decision; it does not tell them what they would need to change to receive a different outcome. Counterfactual explanations (e.g. DiCE library) are on the roadmap for a future release.
4. **Explanation quality degrades if the model is retrained without regenerating the explainer.** A CI check enforces that the explainer is regenerated whenever the model artefact changes.
