"""Deterministic MVP verification engines.

The module keeps each engine behind a small, inspectable function. Production
OCR, LayoutLM, YOLO, issuer APIs and PKCS#7 validation can replace the
implementation without changing the report contract consumed by the UI.
"""
from __future__ import annotations

import hashlib
import io
import math
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover - optional in the minimal demo environment
    fitz = None
try:
    from PIL import Image, ImageChops, ImageStat
except Exception:  # pragma: no cover
    Image = None

RULES = [
    {"id": "APH-DOC-001", "edition": "2024-27", "title": "Mandatory fire safety certificate", "applies_to": "EoA, New", "required_evidence": "fire certificate", "threshold": "unexpired", "severity": "HIGH"},
    {"id": "APH-DOC-002", "edition": "2024-27", "title": "Land ownership / lease evidence", "applies_to": "EoA, New", "required_evidence": "land deed", "threshold": "present", "severity": "HIGH"},
    {"id": "APH-DOC-003", "edition": "2024-27", "title": "Building approval evidence", "applies_to": "EoA, New", "required_evidence": "building plan", "threshold": "present", "severity": "HIGH"},
    {"id": "APH-DOC-004", "edition": "2024-27", "title": "Affidavit freshness", "applies_to": "EoA, New", "required_evidence": "affidavit", "threshold": "<=180 days", "severity": "MEDIUM"},
    {"id": "APH-FAC-001", "edition": "2024-27", "title": "Faculty to intake ratio", "applies_to": "EoA, New", "required_evidence": "faculty list", "threshold": "declared ratio", "severity": "HIGH"},
    {"id": "APH-HIS-001", "edition": "2024-27", "title": "Material historical changes explained", "applies_to": "EoA", "required_evidence": "supporting claim", "threshold": "<=15% unexplained", "severity": "MEDIUM"},
    {"id": "APH-EXT-001", "edition": "2024-27", "title": "Issuer/source verification", "applies_to": "EoA, New", "required_evidence": "DSC, QR or registry receipt", "threshold": "verified or queued", "severity": "HIGH"},
    {"id": "APH-INF-001", "edition": "2024-27", "title": "Infrastructure evidence is geotagged", "applies_to": "EoA, New", "required_evidence": "campus photos", "threshold": "within campus geofence", "severity": "MEDIUM"},
]

WEIGHTS = {"completeness": 20, "authenticity": 25, "consistency": 20, "external": 20, "infrastructure": 15}
REQUIRED = {"fire": ("fire certificate", "fire", "fire safety"), "land": ("land deed", "land", "lease"), "building": ("building approval", "building plan", "building")}


def _text_from_bytes(data: bytes, filename: str = "") -> str:
    if filename.lower().endswith(".pdf") and fitz:
        try:
            doc = fitz.open(stream=data, filetype="pdf")
            return "\n".join(page.get_text() for page in doc)
        except Exception:
            pass
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _kind(filename: str, text: str) -> str:
    lower = f"{filename} {text}".lower()
    for key, words in [("fire certificate", ("fire", "safety")), ("land deed", ("land", "deed", "lease")),
                       ("building approval", ("building", "plan", "approval")), ("affidavit", ("affidavit",)),
                       ("faculty list", ("faculty", "professor")), ("finance", ("balance", "financial")),
                       ("noc", ("noc", "no objection")), ("infrastructure photo", (".jpg", ".jpeg", ".png"))]:
        if any(word in lower for word in words):
            return key
    return "other"


def ela_score(data: bytes) -> Tuple[float, float]:
    """Return (block ratio, risk); a deterministic ELA signal for raster files."""
    if not Image:
        return (1.0, 0.0)
    try:
        image = Image.open(io.BytesIO(data)).convert("RGB")
        compressed = io.BytesIO()
        image.save(compressed, format="JPEG", quality=90)
        recompressed = Image.open(io.BytesIO(compressed.getvalue())).convert("RGB")
        diff = ImageChops.difference(image, recompressed)
        mean = sum(ImageStat.Stat(diff).mean) / 3
        risk = max(0.0, min(0.99, (mean - 2.0) / 18.0))
        return (round(1 + mean / 12, 2), round(risk, 2))
    except Exception:
        return (1.0, 0.0)


def _flag(code: str, engine: str, severity: str, title: str, message: str, doc: str = "", page: int = 1, region: Optional[List[int]] = None) -> Dict[str, Any]:
    return {"code": code, "engine": engine, "severity": severity, "title": title, "message": message,
            "evidence": {"document": doc, "page": page, "region": region or [72, 100, 420, 150]}}


def _claim(key: str, value: Any, confidence: float, doc: str, page: int = 1, region: Optional[List[int]] = None) -> Dict[str, Any]:
    return {"key": key, "value": value, "confidence": confidence, "source_document": doc, "page": page,
            "region": region or [72, 100, 420, 150]}


def _pillars(flags: List[Dict[str, Any]], facts: Dict[str, Any]) -> Dict[str, int]:
    values = {name: 100 for name in WEIGHTS}
    deductions = {"PARSE": "completeness", "PROVE": "authenticity", "MATCH": "consistency", "VERIFY": "external", "SEE": "infrastructure"}
    for flag in flags:
        points = {"LOW": 8, "MEDIUM": 16, "HIGH": 30}.get(flag["severity"], 10)
        key = deductions.get(flag["engine"])
        if key:
            values[key] = max(0, values[key] - points)
    if facts.get("authenticity_override") is not None:
        values["authenticity"] = facts["authenticity_override"]
    return values


def build_report(documents: List[Dict[str, Any]], facts: Optional[Dict[str, Any]] = None, prior: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    facts = facts or {}
    flags: List[Dict[str, Any]] = []
    claims: List[Dict[str, Any]] = []
    present = {str(d.get("kind", "")).lower(): d for d in documents}
    text_blob = "\n".join(str(d.get("text", "")) for d in documents)

    # PARSE: checklist and basic claim extraction.
    for required, aliases in REQUIRED.items():
        found = next((d for k, d in present.items() if any(alias in k for alias in aliases)), None)
        if not found:
            flags.append(_flag(f"MISSING-{required.upper()}", "PARSE", "HIGH", f"Missing {required} evidence", f"The APH mandatory set requires a {required} document.", "checklist", 1))
    date_match = re.search(r"(?:date|issued)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2})", text_blob, re.I)
    if date_match:
        issued = date.fromisoformat(date_match.group(1))
        age = (date.today() - issued).days
        claims.append(_claim("affidavit_date", date_match.group(1), 0.97, "affidavit", 1))
        if age > 180:
            flags.append(_flag("EXPIRED-AFFIDAVIT", "PARSE", "MEDIUM", "Affidavit is expired", f"Issued {age} days ago; APH freshness limit is 180 days.", "affidavit", 1))
    for key, pattern, doc in [("land_acres", r"land\s*(?:area|acres?)\s*[:=]?\s*([0-9.]+)", "land deed"),
                              ("faculty_count", r"faculty\s*(?:count|strength)\s*[:=]?\s*(\d+)", "faculty list"),
                              ("intake", r"intake\s*[:=]?\s*(\d+)", "faculty list")]:
        match = re.search(pattern, text_blob, re.I)
        if match:
            claims.append(_claim(key, float(match.group(1)) if "." in match.group(1) else int(match.group(1)), 0.91, doc))

    # PROVE: ELA, PDF metadata and deliberately visible forensic findings.
    max_risk = 0.0
    for document in documents:
        data = document.get("bytes", b"")
        if data and str(document.get("filename", "")).lower().endswith((".jpg", ".jpeg", ".png")):
            ratio, risk = ela_score(data)
            document.setdefault("metadata", {})["ela_block_ratio"] = ratio
            document["metadata"]["forgery_risk"] = risk
            max_risk = max(max_risk, risk)
            if risk >= 0.55:
                flags.append(_flag("ELA-SUSPECT", "PROVE", "HIGH", "Forensic inconsistency requires inspection", f"ELA risk {risk:.2f}; inspect the highlighted image region and source original.", document.get("name", document.get("filename", ""))))
        lower = str(document.get("text", "")).lower()
        if "forged" in lower or "tampered" in lower or "splice" in lower:
            max_risk = max(max_risk, 0.82)
            flags.append(_flag("PDF-FORENSICS", "PROVE", "HIGH", "Document metadata/content is inconsistent", "The file contains a forensic indicator requiring manual comparison with the issuer copy.", document.get("name", document.get("filename", ""))))
    if facts.get("forged") and not any(f["engine"] == "PROVE" for f in flags):
        max_risk = max(max_risk, 0.82)
        flags.append(_flag("ELA-SUSPECT", "PROVE", "HIGH", "Forensic inconsistency requires inspection", "Synthetic demo tamper signal detected; inspect the heatmap.", facts.get("forged_document", "certificate")))

    # MATCH: history and salted identifiers are represented as non-PII graph keys.
    if facts.get("history_delta"):
        delta = facts["history_delta"]
        claims.append(_claim("land_delta_percent", delta, 0.99, "historical baseline"))
        if abs(float(delta)) > 15:
            flags.append(_flag("HISTORY-JUMP", "MATCH", "MEDIUM", "Unexplained historical change", f"Land claim changed by {delta:+.0f}% against the prior cycle; supporting evidence is required.", "historical baseline"))
    if facts.get("ghost_faculty"):
        claims.append(_claim("faculty_graph_match", facts["ghost_faculty"], 0.99, "faculty list"))
        flags.append(_flag("GHOST-FACULTY", "MATCH", "HIGH", "Shared faculty identifier across institutions", f"Salted graph key {facts['ghost_faculty']} is claimed full-time in another application.", "faculty list"))

    # VERIFY: source channel is advisory unless a confirmed failure is supplied.
    if facts.get("issuer_failure"):
        flags.append(_flag("ISSUER-FAILURE", "VERIFY", "HIGH", "Mandatory issuer verification failed", "The issuer receipt or signature does not validate. Manual issuer confirmation is required.", facts.get("issuer_document", "certificate")))
    elif facts.get("source_verified", True):
        claims.append(_claim("source_channel", facts.get("source_channel", "DigiLocker / signed source receipt"), 0.94, facts.get("issuer_document", "source receipt")))
    else:
        flags.append(_flag("ISSUER-UNREACHABLE", "VERIFY", "LOW", "Issuer endpoint unavailable", "Queued for manual verification; infrastructure failure does not invalidate the applicant.", facts.get("issuer_document", "certificate")))

    # SEE: GPS and perceptual reuse are explicit signals.
    if facts.get("gps_distance_km") is not None:
        distance = float(facts["gps_distance_km"])
        claims.append(_claim("campus_distance_km", distance, 0.98, facts.get("photo_document", "campus photo")))
        if distance > 1.0:
            flags.append(_flag("GPS-OUTLIER", "SEE", "MEDIUM", "Photo is outside campus geofence", f"Photo is {distance:.1f} km from the declared campus.", facts.get("photo_document", "campus photo")))
    if facts.get("photo_reuse"):
        flags.append(_flag("PHOTO-REUSE", "SEE", "HIGH", "Infrastructure photo matches an earlier submission", "Perceptual-hash match attributed to the later submission; inspect the original capture.", facts.get("photo_document", "campus photo")))

    pillars = _pillars(flags, {"authenticity_override": facts.get("authenticity_override")})
    score = round(sum(pillars[key] * WEIGHTS[key] / 100 for key in WEIGHTS))
    high = any(f["severity"] == "HIGH" for f in flags)
    gate = None
    if facts.get("issuer_failure"):
        score = min(score, 40); gate = "mandatory issuer verification failure"
    elif high:
        score = min(score, 58); gate = "unresolved HIGH-severity flag"
    band = "GREEN" if score >= 75 and not high else "AMBER" if score >= 50 else "RED"
    flags.sort(key=lambda f: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(f["severity"], 3))
    return {"score": score, "band": band, "gate": gate, "weights": WEIGHTS, "pillars": pillars,
            "flags": flags, "claims": claims, "checklist": {key: ("PRESENT" if any(key in k for k in present) else "MISSING") for key in REQUIRED},
            "engines": {"PARSE": "complete", "PROVE": "complete", "MATCH": "complete", "VERIFY": "complete", "SEE": "complete"},
            "facts": {k: v for k, v in facts.items() if k not in ("bytes",)}, "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"}


def demo_documents(story: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Small synthetic input set used by seed and by the standalone engine."""
    if story == "green":
        docs = [{"name": "fire certificate", "kind": "fire certificate", "filename": "fire.pdf", "text": "Fire Safety Certificate\nverified source receipt"},
                {"name": "land deed", "kind": "land deed", "filename": "land.pdf", "text": "Land area: 12.4 acres"},
                {"name": "building approval", "kind": "building approval", "filename": "building.pdf", "text": "Building approval"},
                {"name": "affidavit", "kind": "affidavit", "filename": "affidavit.pdf", "text": f"Affidavit date: {(date.today()-timedelta(days=20)).isoformat()}"}]
        return docs, {"source_verified": True, "source_channel": "DigiLocker signed XML", "gps_distance_km": 0.0}
    if story == "red":
        docs = [{"name": "approval scan", "kind": "approval", "filename": "forged.pdf", "text": "FORGED approval splice"}]
        return docs, {"forged": True, "forged_document": "approval scan", "ghost_faculty": "FAC-HASH-2044", "photo_reuse": True, "gps_distance_km": 4.8}
    docs = [{"name": "land deed", "kind": "land deed", "filename": "land.pdf", "text": "Land area: 12.4 acres"},
            {"name": "building approval", "kind": "building approval", "filename": "building.pdf", "text": "Building approval"},
            {"name": "affidavit", "kind": "affidavit", "filename": "affidavit.pdf", "text": f"Affidavit date: {(date.today()-timedelta(days=240)).isoformat()}"},
            {"name": "fire certificate", "kind": "fire certificate", "filename": "forged-fire.pdf", "text": "FORGED stamp splice"}]
    return docs, {"forged": True, "forged_document": "fire certificate", "ghost_faculty": "FAC-HASH-2044", "history_delta": 23, "gps_distance_km": 0.0, "source_verified": False}
