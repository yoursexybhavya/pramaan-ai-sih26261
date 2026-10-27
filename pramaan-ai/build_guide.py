#!/usr/bin/env python3
"""Generate the step-by-step PRAMAAN-AI implementation and operations guide."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "PRAMAAN_AI_Implementation_and_Operations_Guide.pdf"
NAVY = colors.HexColor("#102d45"); TEAL = colors.HexColor("#087f82"); SAFFRON = colors.HexColor("#e88b39")

SECTIONS = [
    ("1 · What PRAMAAN-AI does", [
        "PRAMAAN-AI is a decision-support layer for AICTE application validation. It reads submitted evidence, extracts typed claims, runs five independent verification engines, and produces a Trust Score with linked inspection evidence.",
        "GREEN means fast-track desk review, AMBER means focused scrutiny, and RED means priority EVC inspection. These labels never approve or reject an institution.",
        "The system is intentionally deterministic where possible. Optional AI is advisory for perception and claim suggestions; APH rules, hard gates and human decisions remain authoritative.",
    ]),
    ("2 · End-to-end data flow", [
        "Step 1 — A reviewer logs in with a role. Evaluator reviews and uploads; Senior Official records the final decision; Admin governs; Auditor verifies the chain.",
        "Step 2 — Documents are classified and text is extracted. PDF text extraction is active in the MVP; OCR and layout models are replaceable adapters.",
        "Step 3 — The Claim Graph stores a value, confidence, source document, page and bounding-region reference.",
        "Step 4 — PARSE, PROVE, MATCH, VERIFY and SEE evaluate claims independently. A failure of one engine does not silently disappear.",
        "Step 5 — Weighted pillars and hard gates produce the score. Flags link to exact evidence. The official accepts, overrides with a reason, or records a decision.",
        "Step 6 — Every ingest, engine run, flag action, decision and verification is appended to a SHA-256 hash chain.",
    ]),
    ("3 · The five engines", [
        "PARSE checks mandatory evidence, expiry and basic claim arithmetic against the versioned APH Rule Graph.",
        "PROVE computes block-wise ELA and exposes forensic signals. The wording is ‘inconsistent with an untampered original; inspect here’, never an automatic forgery verdict.",
        "MATCH compares historical metrics and salted faculty identifiers. A shared graph key is evidence for inspection, not a public identity disclosure.",
        "VERIFY ranks source strength: signed issuer source, DSC, QR/issuer endpoint and registry receipt. An unreachable issuer becomes a manual-verify item, not an invalid submission.",
        "SEE checks geofence, image reuse and future object-count seams. The output is a precise EVC agenda rather than a generic visit request.",
    ]),
    ("4 · Trust Score and governance", [
        "Pillars: completeness 20%, authenticity 25%, consistency 20%, external verification 20%, infrastructure plausibility 15%.",
        "Hard gates: an unresolved HIGH flag caps the score at 58; a confirmed mandatory issuer-verification failure caps it at 40.",
        "The score is a prioritisation aid. The dashboard enforces role-based approval and requires reasons for overrides and negative decisions.",
        "Impact values in the project are design targets until validated in shadow mode. Seeded files and prototype outputs are synthetic and labelled accordingly.",
    ]),
    ("5 · AI provider policy — no leaked keys", [
        "There are no legitimate ‘open-source API keys’ to copy from the internet. Public keys are usually stolen, revoked, rate-limited or unsafe to use. Never put a key in JavaScript, Git, a PDF, or a screenshot.",
        "The default is rules-only mode: AI_PROVIDER=disabled. The application still works and the regulatory checks remain auditable.",
        "For a no-key local model, install Ollama and run a model on the reviewer machine. Local Ollama at http://localhost:11434 does not require authentication.",
        "For a hosted provider, set PRAMAAN_AI_BASE_URL, PRAMAAN_AI_MODEL and PRAMAAN_AI_API_KEY as server-side environment variables. The status endpoint reports only whether a key is present, never its value.",
        "The optional provider can suggest claims, but suggestions are marked advisory_only and are not used to auto-approve, auto-reject or bypass hard gates.",
    ]),
    ("6 · Local Ollama setup (no API key)", [
        "Install Ollama from https://ollama.com/download and start the local service.",
        "Download a suitable local model, for example: ollama pull gemma3:4b. Select a model that fits the available RAM/GPU and the institution’s data policy.",
        "From pramaan-app, set: export AI_PROVIDER=ollama; export OLLAMA_BASE_URL=http://localhost:11434; export OLLAMA_MODEL=gemma3:4b.",
        "Start the app with ./run.sh, log in, and call GET /api/ai/status through the dashboard session. ‘available: true’ means the local endpoint responded.",
        "If Ollama is stopped or slow, the request falls back to deterministic rules. A model outage never changes a compliance result.",
    ]),
    ("7 · Hosted AI and official integrations", [
        "Recommended hosted choices: Groq’s free developer access for fast open-weight models; OpenRouter’s openrouter/free router for zero-cost, rate-limited model routing; or Cerebras’ time-limited trial credits. Availability and quotas change, so verify the provider’s current terms.",
        "Create credentials only in the provider’s official console. Store them in Vercel Environment Variables or a secret manager; use separate Development, Preview and Production values.",
        "DigiLocker/API Setu is not an open anonymous API. It requires partner registration, consent and issued credentials such as client ID, client secret or product instance ID depending on the integration path.",
        "Use official sandbox credentials and signed receipts. A copied document uploaded to DigiLocker must not be treated as issuer-authenticated merely because it is hosted there.",
        "For PaddleOCR, local deployment is open source. Hosted PaddleOCR services require their own access token. Add that integration only behind a server-side adapter and preserve confidence/routing metadata.",
    ]),
    ("8 · Run, test and demonstrate", [
        "Install: cd pramaan-app; python3 -m venv .venv; . .venv/bin/activate; pip install -r requirements.txt.",
        "Run: ./run.sh, then open http://localhost:8000. Demo password for evaluator, senior, admin and auditor is demo123.",
        "Walkthrough: log in as evaluator → open RED file → inspect PROVE heatmap and page evidence → accept or override with reason → switch to Senior Official → record a human decision → verify audit chain.",
        "Offline engine: python3 pramaan-ai/engine/pramaan_engine.py. It prints clean/tampered ELA risk, the 52/100 demo score and audit validity.",
        "Checks: compile Python, run the API flow, verify Evaluator approval returns 403, verify override without reason returns 400, and verify the audit chain is VALID.",
    ]),
    ("9 · Deployment and production hardening", [
        "The Vercel demo uses a Python function and ephemeral /tmp SQLite/upload storage. It is suitable for a demo, not durable production records.",
        "Production must move persistence to PostgreSQL, evidence to encrypted object storage, background processing to a worker queue, and authentication to AICTE SSO/e-sign infrastructure.",
        "Set PRAMAAN_SECRET to a random server-side secret in production. Rotate demo passwords, restrict CORS, configure retention, encrypt backups and monitor model/flag precision by data stratum.",
        "Use shadow mode before decisions are affected. An engine that misses its agreed threshold remains advisory-only.",
    ]),
    ("10 · API and reference links", [
        "Core API: POST /api/login; GET /api/me; GET /api/ai/status; GET /api/applications; POST /api/applications; POST /api/applications/{id}/decide; POST /api/audit/verify.",
        "Official Ollama API: https://docs.ollama.com/api/generate and https://docs.ollama.com/api/authentication.",
        "PaddleOCR: https://paddlepaddle.github.io/PaddleOCR/main/en/index.html.",
        "DigiLocker/API Setu: https://apisetu.gov.in/digilocker and https://docs.setu.co/data/digilocker/quickstart.",
        "Repository: https://github.com/yoursexybhavya/pramaan-ai-sih26261. Production demo: https://pramaan-ai-sih26261.vercel.app.",
    ]),
]

def wrap(c, text, x, y, width, size=12.5, leading=17):
    line = ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if line and c.stringWidth(trial, "Helvetica", size) > width:
            c.drawString(x, y, line); y -= leading; line = word
        else: line = trial
    if line: c.drawString(x, y, line); y -= leading
    return y

def main():
    c = canvas.Canvas(str(OUT), pagesize=A4); w, h = A4
    for number, (title, bullets) in enumerate(SECTIONS, 1):
        c.setFillColor(NAVY); c.rect(0, h - 35*mm, w, 35*mm, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 21); c.drawString(20*mm, h-21*mm, "PRAMAAN-AI")
        c.setFont("Helvetica", 8.5); c.drawRightString(w-20*mm, h-21*mm, f"IMPLEMENTATION GUIDE · {number:02d}/{len(SECTIONS)}")
        c.setFillColor(TEAL); c.setFont("Helvetica-Bold", 17); c.drawString(20*mm, h-51*mm, title)
        y = h - 68*mm
        for bullet in bullets:
            c.setFillColor(SAFFRON); c.circle(25*mm, y+2, 1.8*mm, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#142638")); y = wrap(c, bullet, 34*mm, y, w-55*mm) - 5
        c.setStrokeColor(colors.HexColor("#dce6ea")); c.line(20*mm, 17*mm, w-20*mm, 17*mm)
        c.setFillColor(colors.HexColor("#6b7b88")); c.setFont("Helvetica", 8); c.drawString(20*mm, 10*mm, "CtrlAltElite · synthetic demo · AI advises, human decides")
        c.showPage()
    c.save(); print(OUT)

if __name__ == "__main__": main()
