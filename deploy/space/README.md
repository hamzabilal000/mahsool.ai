---
title: Mahsool AI API
emoji: 🧾
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Pakistani income tax Q&A with section-level citations (API)
---

# Mahsool AI — API

Backend of [Mahsool AI](https://github.com/hamzabilal000/mahsool.ai): answers questions about Pakistani income tax
law in English, Urdu and Roman Urdu, citing the Income Tax Ordinance 2001, the Income Tax Rules 2002 and FBR's
withholding tax rate card (tax year 2027). For information only, not tax advice.

Endpoints: `POST /ask`, `POST /ask/stream`, `POST /feedback`, `GET /eval/summary`, `GET /health`; docs at `/docs`.
This Space is built from the GitHub repository by `scripts/deploy_space.py`.
