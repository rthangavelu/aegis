# Supply Chain Risk Review — Credit Scoring v3
<!-- mock: true -->

**System:** credit-scoring-v3  
**Review date:** 2026-01-15  
**Reviewer:** Risk Officer  
**Next review:** 2027-01-15

---

## Vendor assessment

| Component | Vendor | Type | Risk | Documentation |
|-----------|--------|------|------|---------------|
| Training dataset | Experian (synthetic mock) | Dataset | Medium | Data card v2 available |
| Feature engineering library | scikit-learn 1.4 | Open source | Low | PyPI release notes, CVE monitoring via Dependabot |
| Model serving infrastructure | AWS SageMaker (mock) | Cloud API | Medium | SOC 2 Type II (annual renewal) |
| Monitoring platform | Internal | In-house | Low | N/A |

All vendors have been assessed for fitness for purpose, data protection obligations, and regulatory compliance with EU AI Act Arts. 25-28. No high-risk vendors identified. The synthetic dataset used for testing does not contain real personal data.

---

## Contractual controls

The following contractual provisions are in place for medium-risk vendors:

- **Data Processing Agreement (DPA)** executed with dataset provider covering GDPR Art. 28 obligations, data retention limits (5 years), and right to audit.
- **Service Agreement** with cloud infrastructure provider includes: incident notification within 24 hours, right-to-audit clause (annual), data residency restriction to EU/EEA, and model change notification with 30-day lead time.
- **Open-source policy** reviewed and approved by Legal: all dependencies are Apache 2.0 or BSD licenced. No GPL dependencies in the inference path.
- Annual review gate: Risk Officer reviews all contracts before renewal.

---

## Ongoing monitoring

| Activity | Frequency | Owner | Last completed |
|----------|-----------|-------|----------------|
| Dependabot / OSV vulnerability scan | Continuous (automated) | ML Engineer | 2026-01-14 |
| Vendor SOC 2 certificate renewal check | Annual | Risk Officer | 2026-01-15 |
| Dataset drift and provenance re-review | Quarterly | ML Lead | 2025-10-01 |
| Contractual controls review | Annual | Legal | 2026-01-10 |
| Incident log review | Quarterly | Risk Officer | 2025-10-01 |

No supply chain incidents were identified in the last 12 months. The ML Engineer monitors the GitHub security advisories feed for all pinned dependencies.
