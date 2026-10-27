#!/usr/bin/env python3
"""Build the six-slide SIH idea presentation from the official PDF template.

The SIH instructions require a maximum of six slides including the title slide
and require submission as PDF.  This script keeps the official template pages,
removes the placeholder copy, and adds the PRAMAAN-AI content as readable
bullets.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "assets" / "SIH2026_Official_IDEA_Presentation_Format.pdf"
OUT = ROOT.parent / "CtrlAltElite_PRAMAAN_SIH26261_Presentation.pdf"
W, H = 960, 540

NAVY = colors.HexColor("#214c84")
BODY = colors.black
WHITE = colors.white


SLIDES = [
    [
        "PRAMAAN-AI",
        "Provenance-anchored Regulatory AI for Approval, Authentication & Norm-compliance",
        "Problem Statement ID — SIH26261",
        "Problem Statement Title — AI-Powered Application Validation, Document Authentication & Regulatory Compliance Verification",
        "Theme — Smart Automation",
        "PS Category — Software",
        "Team ID — CtrlAltElite",
        "Team Name — CtrlAltElite",
    ],
    [
        "PRAMAAN-AI: PROOF, NOT PAPERWORK",
        "PRAMAAN-AI is an AI pre-scrutiny layer between the AICTE portal and the evaluator's desk.",
        "PARSE — checks APH completeness, expiry, prescribed formats and arithmetic before review.",
        "PROVE — uses ELA, metadata, fonts, signatures and copy/splice inspection to surface evidence.",
        "MATCH + VERIFY + SEE — history/faculty graph, DigiLocker/API Setu/DSC/QR, GPS and photo-reuse checks.",
        "Innovation — APH-as-Code, claim-level page/region evidence, explainable Trust Score and hard gates.",
        "AI advises; the authorised human official decides. No black-box verdicts.",
    ],
    [
        "TECHNICAL APPROACH",
        "Flow — AICTE portal/upload → PARSE → Claim Graph → five engines → Trust Score → evidence report → human decision/EVC.",
        "Stack — Python/FastAPI MVP + reviewer dashboard; production seams for PaddleOCR, LayoutLMv3, YOLOv8, OpenCV/ELA, PostgreSQL, Redis and MinIO.",
        "Method — ingest and classify; extract claims with coordinates; run engines in parallel; score with explainable weights and hard gates; report; learn from human review.",
        "Working prototype — offline engine, FastAPI application and reviewer dashboard are included with the submission.",
        "Reproducible demo — clean ELA risk 0.00 vs tampered 0.83; demo Trust Score 52/100 (AMBER); seven-entry SHA-256 audit chain verifies.",
    ],
    [
        "FEASIBILITY AND VIABILITY",
        "Feasible now — open-source technology, commodity CPU/GPU compute, standard issuer interfaces and an API sidecar to the existing portal.",
        "Scans or regional-language documents → OCR confidence routing; missing labels → synthetic tamper generator plus forensic signals.",
        "Issuer outage → DSC/QR/manual-verify queue, never automatic rejection; privacy → RBAC, salted graph keys, redaction and on-prem/VPC deployment.",
        "Adoption — advisory-only rollout keeps official authority; APH-as-Code absorbs handbook changes without a rewrite.",
        "Roadmap — Phase 0 pilot → Phase 1 shadow mode → Phase 2 assisted live triage → Phase 3 scale and learn.",
        "Kill criterion — an underperforming engine stays advisory-only until shadow-mode evidence supports it.",
    ],
    [
        "IMPACT AND BENEFITS",
        "Design target — approximately 80% less pre-scrutiny effort and first feedback in days rather than weeks.",
        "100% evidence-linked — every flag opens the exact source page/region; only RED is prioritised for EVC inspection first.",
        "Institutions — instant deficiency lists, fewer rejection cycles and predictable cure timelines.",
        "Evaluators — less page-turning and more judgement; effort shifts to AMBER/RED cases where it matters.",
        "AICTE and the system — fraud-pattern intelligence, stronger deterrence and fewer unnecessary physical visits or paper files.",
        "Projected triage mix — 58% GREEN, 29% AMBER, 13% RED. All impact figures are targets to validate in shadow mode.",
    ],
    [
        "RESEARCH AND REFERENCES",
        "AICTE Approval Process Handbook 2024–25 to 2026–27 — norms, checklists and EoA process: aicte-india.org.",
        "DigiLocker Issuer/Requester API specifications and API Setu (NeGD, MeitY) — signed-source verification model.",
        "LayoutLMv3 (ACM Multimedia 2022), PaddleOCR, OpenCV/ELA and copy-move detection literature — document and image forensics.",
        "Ultralytics YOLOv8 for infrastructure audit seams; NIST and OWASP guidance for RBAC, audit logging and tamper-evident records.",
        "Built for this hackathon — offline engine, FastAPI app, reviewer dashboard, Trust Score and hash-chain audit. Prototype data is synthetic; impact figures are targets, not measured claims.",
        "PRAMAAN-AI does not replace an AICTE official. It removes paperwork standing between officials and their judgement.",
    ],
]


def wrapped_lines(c: canvas.Canvas, text: str, font: str, size: float, width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        trial = f"{line} {word}".strip()
        if line and c.stringWidth(trial, font, size) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def draw_bullet_list(c: canvas.Canvas, bullets: list[str], x: float, y: float, width: float, size: float = 15.5) -> None:
    leading = size * 1.18
    gap = 6
    for bullet in bullets:
        c.setFillColor(BODY)
        c.setFont("Helvetica", size)
        lines = wrapped_lines(c, bullet, "Helvetica", size, width - 28)
        c.drawString(x, y, "•")
        for index, line in enumerate(lines):
            c.drawString(x + 26, y - index * leading, line)
        y -= len(lines) * leading + gap


def cover_placeholder_area(c: canvas.Canvas) -> None:
    c.setFillColor(WHITE)
    c.rect(28, 78, 900, 300, fill=1, stroke=0)


def draw_team_badge(c: canvas.Canvas) -> None:
    # Keep the purple outline from the template and replace only its placeholder text.
    c.setFillColor(WHITE)
    c.ellipse(30, 456, 122, 532, fill=1, stroke=0)
    c.setFillColor(BODY)
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(76, 494, "CtrlAltElite")


def make_overlay(slide_number: int) -> bytes:
    stream = BytesIO()
    c = canvas.Canvas(stream, pagesize=(W, H))

    if slide_number == 1:
        # Preserve the official title-page artwork while replacing all placeholders.
        c.setFillColor(WHITE)
        c.rect(0, 45, 470, 380, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.rect(270, 394, 430, 66, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont("Times-Bold", 30)
        c.drawString(68, 414, SLIDES[0][0])
        c.setFillColor(BODY)
        c.setFont("Helvetica", 13.5)
        subtitle = wrapped_lines(c, SLIDES[0][1], "Helvetica", 13.5, 390)
        y = 386
        for line in subtitle:
            c.drawString(68, y, line)
            y -= 17
        c.setFont("Helvetica-Bold", 12.2)
        y -= 14
        for field in SLIDES[0][2:]:
            lines = wrapped_lines(c, field, "Helvetica-Bold", 12.2, 400)
            for line in lines:
                c.drawString(52, y, line)
                y -= 16
            y -= 7
    else:
        draw_team_badge(c)
        cover_placeholder_area(c)
        # The template's body bullets are indented farther left than its copy.
        # Remove those stray bullet glyphs while leaving the blue section marker.
        c.setFillColor(WHITE)
        c.rect(0, 188, 26, 108, fill=1, stroke=0)
        if slide_number == 2:
            # The official template says IDEA TITLE; use the actual idea title.
            c.setFillColor(WHITE)
            c.rect(245, 447, 500, 55, fill=1, stroke=0)
            c.setFillColor(BODY)
            c.setFont("Times-Bold", 25)
            c.drawCentredString(W / 2, 472, SLIDES[1][0])
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Bold", 22)
            c.drawString(16, 350, "❖ Proposed Solution (Describe your Idea/Solution/Prototype)")
        c.setFillColor(BODY)
        body_y = 326 if slide_number == 2 else 338
        draw_bullet_list(c, SLIDES[slide_number - 1][1:], 52, body_y, 842, 15.4)

    c.save()
    return stream.getvalue()


def main() -> None:
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Official template not found: {TEMPLATE}")
    source = PdfReader(str(TEMPLATE))
    writer = PdfWriter()
    for index in range(6):
        page = source.pages[index]
        overlay = PdfReader(BytesIO(make_overlay(index + 1))).pages[0]
        # PyPDF2 places the added page below the target page, so the overlay is
        # merged into the template page to keep masks and new copy visible.
        page.merge_page(overlay)
        writer.add_page(page)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("wb") as handle:
        writer.write(handle)
    print(OUT)


if __name__ == "__main__":
    main()
