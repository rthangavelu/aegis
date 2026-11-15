# MOCK DATA — Model Card: Customer Support Chatbot

**Last updated:** 2026-08-15
**Owner:** cx-team@example.com
**Risk tier:** Limited
**Version:** 1.4.2

## Model details

Large language model fine-tuned on support tickets and knowledge-base articles.
Escalates to a human agent when confidence < 0.60 or when the customer requests it.

## Intended use

First-line customer support for billing and product queries. Not used for
financial or medical advice.

## Training data

Internal ticket history 2022–2025 (500k tickets) plus product documentation.
No personal customer data included in training.

## Safety

Human escalation path tested monthly. Last test: 2026-10-20.
