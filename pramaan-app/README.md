# PRAMAAN-AI working application

FastAPI + SQLite MVP for SIH26261. It provides login/RBAC, a seeded
risk-ranked queue, APH rule graph, five-engine report contract, evidence-linked
flags, upload-to-score flow, human decision guardrails, and a hash-chained
audit trail.

## Run

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

Open <http://localhost:8000>. Demo password for `evaluator`, `senior`,
`admin`, and `auditor` is `demo123`.

The MVP deliberately uses deterministic rules and optional PDF/image parsers.
PaddleOCR, LayoutLMv3, YOLO, live DigiLocker/API Setu connectors and
production SSO are clean engine seams for Phase 2; issuer unavailability is
represented as a manual-verify queue, never an automatic invalidation.
