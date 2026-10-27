# PRAMAAN-AI offline prototype

This standalone prototype uses only Python and Pillow to demonstrate the
riskiest explainability path: real block-wise Error Level Analysis, a
five-pillar Trust Score, evidence-linked flags, and a verifiable SHA-256
audit chain.

```bash
python3 engine/pramaan_engine.py
python3 engine/make_assets.py
python3 -m http.server 8765
# open http://localhost:8765/prototype/
```

All data is synthetic. A forensic signal is an inspection request, not a
legal finding of forgery.
