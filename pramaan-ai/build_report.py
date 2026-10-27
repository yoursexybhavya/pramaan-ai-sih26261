#!/usr/bin/env python3
"""Build a compact, honest 14-page detailed solution PDF."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "CtrlAltElite_PRAMAAN_SIH26261_Detailed_Solution.pdf"
NAVY = colors.HexColor("#102d45"); TEAL = colors.HexColor("#087f82"); SAFFRON = colors.HexColor("#e88b39")

PAGES = [
 ("Executive Summary", ["PRAMAAN-AI is a secure AI decision-support layer between the AICTE portal and the evaluator.", "Five engines parse, prove, match, verify and see; a versioned APH Rule Graph evaluates machine-readable norms.", "Every claim retains source page, region and confidence. Trust Score 0–100 routes GREEN, AMBER or RED.", "AI is advisory only; an authorised human official records the final decision."]),
 ("Problem Analysis & Traceability", ["Manual inspection creates late deficiencies, inconsistent scrutiny and preventable EVC visits.", "R1 PARSE → completeness and expiry; R2 PROVE → forensic inspection; R3 MATCH → historical and faculty graph.", "R4 VERIFY → issuer/source receipts; R5 SEE → GPS, counts and photo reuse; R6 → evidence report.", "R7 queue → EVC prioritisation; R8 → hash-chain audit; R9 → human decision guardrail."]),
 ("Solution Overview", ["APH-as-Code: clause, applicability, evidence, threshold, severity and handbook edition are configuration.", "Claim Graph: typed claims are the unit of verification, not opaque document blobs.", "Six steps: ingest → classify/extract → build claims → run independent engines → score/triage → human decision.", "Configuration changes are versioned and diff-reviewed before activation."]),
 ("The Five Verification Engines", ["PARSE: PDF text/layout seam, checklist, expiry, prescribed format and arithmetic checks.", "PROVE: ELA, metadata/font signals and copy/splice inspection; output is an inspection request.", "MATCH: year-on-year deltas and salted faculty identifiers catch unexplained changes and ghost faculty.", "VERIFY: source-channel strength is ordered DigiLocker/API, DSC, QR and registry; unavailable is manual queue.", "SEE: geofence, photo reuse and future object-count seam produce a focused EVC agenda."]),
 ("Trust Score & Triage", ["Weights: completeness 20%, authenticity 25%, consistency 20%, external 20%, infrastructure 15%.", "Hard gates: unresolved HIGH caps 58; confirmed mandatory issuer failure caps 40.", "GREEN ≥75 without HIGH; AMBER 50–74 or capped; RED <50 or gate breach.", "Synthetic demonstration: 52/100 AMBER; authenticity collapses to 17/100 because of one suspect document."]),
 ("System Architecture", ["MVP: FastAPI, SQLite, PyMuPDF/Pillow seams, reportlab seed data and an offline single-page dashboard.", "Production posture: PostgreSQL, object storage, workers/queue, GPU pool, RBAC/SSO and AICTE VPC deployment.", "Stable contracts let heavier OCR, LayoutLM, YOLO, issuer APIs and PKCS#7 validation replace MVP adapters.", "Evidence and audit records are persisted independently from UI rendering."]),
 ("Reviewer Experience & Workflows", ["Evaluator opens the risk-ranked queue, selects a submission and follows each flag to source document/page/region.", "Accepted/overridden flags require an audit event; overrides require a reason.", "Senior Official is the only role permitted to Approve, Reject or Return for cure.", "RED creates a ready-made EVC agenda: inspect the exact room, document or issuer claim first."]),
 ("Prototype Implementation & Results", ["Standalone engine and live app are included in this repository; all seed values are synthetic.", "Reproducible output: clean/tampered image ELA, 52-point report, eight flags and a valid seven-entry chain.", "Live upload path: multipart evidence → extraction → five-engine report → queue → decision → audit.", "Prototype output is real code output; target impact figures are not claimed as measured."]),
 ("Security, Privacy & Governance", ["Role matrix: Evaluator reviews, Senior Official decides, Admin governs, Auditor verifies.", "Salted faculty graph keys avoid exposing raw identity in analytics; PII is minimised and deployment can be on-prem.", "SHA-256 previous-hash links make changes detectable; chain verification is a reviewer action.", "Random GREEN re-checks, per-engine shadow metrics and confidence routing address automation bias."]),
 ("Feasibility, Roadmap & Delivery", ["Phase 0: offline pilot; every flag must be evidence-linked. Phase 1: shadow mode beside manual scrutiny.", "Phase 2: assisted live triage and deficiency view. Phase 3: all application types and next APH rule pack.", "Poor scans → OCR ensemble and human routing; unavailable issuer → manual queue; sophisticated forgery → defence in depth.", "Kill criterion: underperforming engines stay advisory-only."]),
 ("Impact, Benefits & Measurement", ["Design targets: ~80% less pre-scrutiny effort, feedback in days, 55–60% desk-clearable.", "Measure minutes/application, time-to-first-deficiency, flag precision/recall, EVC precision and override rate in shadow mode.", "Institutions gain predictable cure loops; evaluators spend time on judgement; AICTE gains fraud-pattern intelligence.", "Fewer repeat visits and paper handling support environmental benefit."]),
 ("Risks, Limitations & Ethics", ["A flag is not a finding of forgery. Human officials retain authority and applicants retain a cure path.", "Regional-language scans, false positives and adversarial forgery require stratified validation, not one average accuracy.", "MVP interfaces OCR, YOLO, live issuer APIs and production identity; it does not pretend those integrations are live.", "Data governance, retention, access logging and issuer agreements are delivery gates."]),
 ("Research & References", ["AICTE Approval Process Handbook 2024–25 to 2026–27.", "DigiLocker Issuer/Requester API specifications and API Setu (NeGD/MeitY).", "LayoutLMv3 (ACM Multimedia 2022); PaddleOCR; ELA and copy-move literature; Ultralytics YOLO.", "NIST SP 800-92; OWASP logging/RBAC guidance; PDF CMS/PKCS#7 validation practice."]),
 ("Appendices · Rule Extract · File Guide · Glossary", ["APH-DOC-001: fire safety certificate · EoA/New · unexpired · HIGH.", "APH-EXT-001: issuer/source receipt · EoA/New · verified or queued · HIGH.", "Run: pramaan-app/run.sh for the application; python3 pramaan-ai/engine/pramaan_engine.py for the offline engine.", "APH = Approval Process Handbook · DSC = Digital Signature Certificate · ELA = Error Level Analysis · EVC = Expert Visiting Committee."]),
]

def wrap(c, text, x, y, width, size=13, leading=18):
    words=text.split(); line=""
    for word in words:
        trial=(line+" "+word).strip()
        if c.stringWidth(trial, "Helvetica", size)>width:
            c.drawString(x,y,line); y-=leading; line=word
        else: line=trial
    if line: c.drawString(x,y,line); y-=leading
    return y

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True); c=canvas.Canvas(str(OUT), pagesize=A4); w,h=A4
    for index,(title, bullets) in enumerate(PAGES,1):
        c.setFillColor(NAVY); c.rect(0,h-38*mm,w,38*mm,fill=1,stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold",22); c.drawString(22*mm,h-22*mm,"PRAMAAN-AI")
        c.setFont("Helvetica",9); c.drawRightString(w-22*mm,h-22*mm,f"SIH26261 · {index:02d}/14")
        c.setFillColor(TEAL); c.setFont("Helvetica-Bold",18); c.drawString(22*mm,h-55*mm,title)
        y=h-72*mm; c.setFillColor(colors.HexColor("#142638"))
        for bullet in bullets:
            c.setFillColor(SAFFRON); c.circle(27*mm,y+2,2.1*mm,fill=1,stroke=0); c.setFillColor(colors.HexColor("#142638")); y=wrap(c,bullet,36*mm,y,w-58*mm)+9
        c.setStrokeColor(colors.HexColor("#dce6ea")); c.line(22*mm,18*mm,w-22*mm,18*mm); c.setFillColor(colors.HexColor("#6b7b88")); c.setFont("Helvetica",8); c.drawString(22*mm,11*mm,"Team CtrlAltElite · synthetic prototype · AI advises, human decides")
        c.showPage()
    c.save(); print(OUT)

if __name__=="__main__": main()
