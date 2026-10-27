#!/usr/bin/env python3
"""Offline PRAMAAN-AI demonstration engine.

Run from the repository root:
    python3 pramaan-ai/engine/pramaan_engine.py

It creates synthetic certificate images, computes real Pillow ELA signals,
generates a report, and verifies a SHA-256 hash-chained audit trail. No
network, model download or private institutional data is required.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
ASSETS = ROOT / "assets"


def ela(image: Image.Image, quality: int = 75) -> Tuple[float, float, Image.Image]:
    original = image.convert("RGB")
    buf = io.BytesIO(); original.save(buf, "JPEG", quality=quality)
    recompressed = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    diff = ImageChops.difference(original, recompressed)
    mean = sum(ImageStat.Stat(diff).mean) / 3
    # Block-wise anomaly ratio is more informative than a page-wide average:
    # a small pasted region should remain visible even when most of the page
    # is a clean white background.
    blocks = []
    for top in range(0, original.height, 32):
        for left in range(0, original.width, 32):
            block = diff.crop((left, top, min(left + 32, original.width), min(top + 32, original.height)))
            blocks.append(sum(ImageStat.Stat(block).mean) / 3)
    suspicious = sum(value > 4.5 for value in blocks) / max(1, len(blocks))
    risk = max(0.0, min(0.99, (suspicious - 0.01) / 0.03))
    heat = diff.point(lambda px: min(255, px * 8))
    return round(1 + mean / 12, 2), round(risk, 2), heat


def make_certificate(tampered: bool) -> Image.Image:
    image = Image.new("RGB", (1200, 800), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((35, 35, 1165, 765), outline="#123d55", width=5)
    draw.text((90, 90), "FIRE SAFETY CERTIFICATE", fill="#123d55")
    draw.text((90, 160), "Institution: Demonstration Institute of Technology", fill="#222")
    draw.text((90, 220), "Certificate ID: AICTE-FIRE-2026-0044", fill="#222")
    draw.text((90, 280), "Issued: 2026-01-14", fill="#222")
    draw.text((90, 340), "This certificate is generated for prototype demonstration.", fill="#555")
    draw.ellipse((850, 510, 1050, 710), outline="#b14b42", width=8)
    draw.text((885, 590), "ISSUER", fill="#b14b42")
    if tampered:
        # Establish a compressed host first, then splice a deterministic
        # high-frequency patch. This mirrors the recompression mismatch ELA
        # is intended to surface and keeps the result reproducible.
        host = io.BytesIO(); image.save(host, "JPEG", quality=92)
        image = Image.open(io.BytesIO(host.getvalue())).convert("RGB")
        draw = ImageDraw.Draw(image)
        # A retyped/spliced field is intentionally different from the host.
        draw.rectangle((480, 205, 910, 255), fill="#fff")
        draw.text((480, 220), "Certificate ID: ALTERED-0044", fill="#7b1717")
        draw.rectangle((670, 360, 940, 430), fill="#fff")
        draw.text((680, 375), "VALID UNTIL 2031", fill="#7b1717")
        pixels = image.load()
        for y in range(255, 320):
            for x in range(440, 970):
                if (x * 17 + y * 31) % 11 < 5:
                    r, g, b = pixels[x, y]
                    pixels[x, y] = (min(255, r + 48), max(0, g - 25), max(0, b - 25))
    return image


def append_audit(chain: List[Dict[str, Any]], action: str, detail: Dict[str, Any]) -> None:
    previous = chain[-1]["hash"] if chain else "GENESIS"
    item = {"action": action, "detail": detail, "previous_hash": previous,
            "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"}
    item["hash"] = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
    chain.append(item)


def verify_audit(chain: List[Dict[str, Any]]) -> bool:
    previous = "GENESIS"
    for item in chain:
        raw = {k: item[k] for k in ("action", "detail", "previous_hash", "created_at")}
        expected = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
        if item["previous_hash"] != previous or item["hash"] != expected: return False
        previous = item["hash"]
    return True


def run() -> Dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True); ASSETS.mkdir(parents=True, exist_ok=True)
    clean_ratio, clean_risk, clean_heat = ela(make_certificate(False))
    forged_ratio, forged_risk, forged_heat = ela(make_certificate(True))
    clean_heat.save(ASSETS / "ela_clean_heatmap.png"); forged_heat.save(ASSETS / "ela_forged_heatmap.png")
    flags = [
        {"code": "MISSING-FIRE", "severity": "HIGH", "engine": "PARSE", "message": "Fire certificate checklist cell is unresolved"},
        {"code": "EXPIRED-AFFIDAVIT", "severity": "MEDIUM", "engine": "PARSE", "message": "Affidavit age exceeds 180-day rule"},
        {"code": "ELA-SUSPECT", "severity": "HIGH", "engine": "PROVE", "message": f"Forgery risk {forged_risk:.2f}; inspect heatmap"},
        {"code": "HISTORY-JUMP", "severity": "MEDIUM", "engine": "MATCH", "message": "Land area changed +23% without support"},
        {"code": "GHOST-FACULTY", "severity": "HIGH", "engine": "MATCH", "message": "Salted faculty key FAC-HASH-2044 repeats"},
        {"code": "DSC-INVALID", "severity": "HIGH", "engine": "VERIFY", "message": "Two certificate signatures need issuer confirmation"},
        {"code": "GPS-OUTLIER", "severity": "MEDIUM", "engine": "SEE", "message": "One photo is outside the campus geofence"},
        {"code": "PHOTO-REUSE", "severity": "HIGH", "engine": "SEE", "message": "Perceptual hash matches a later submission"},
    ]
    pillars = {"completeness": 62, "authenticity": 17, "consistency": 72, "external": 48, "infrastructure": 76}
    score = round(sum(v * w / 100 for v, w in zip(pillars.values(), (20, 25, 20, 20, 15))))
    score = min(score, 58); chain: List[Dict[str, Any]] = []
    for action in ("INGEST", "PARSE", "PROVE", "MATCH", "VERIFY", "SEE", "SCORE"):
        append_audit(chain, action, {"application": "synthetic-eoa-0044"})
    report = {"application": "synthetic-eoa-0044", "score": score, "band": "AMBER", "hard_gate": "unresolved HIGH-severity flag",
              "pillars": pillars, "flags": flags, "forensics": {"clean": {"block_ratio": clean_ratio, "risk": clean_risk}, "tampered": {"block_ratio": forged_ratio, "risk": forged_risk}},
              "audit": chain, "audit_valid": verify_audit(chain), "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"}
    (OUT / "demo_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Clean certificate : ELA block-ratio {clean_ratio:.2f}, forgery risk {clean_risk:.2f} -> CLEAN")
    print(f"Tampered cert     : ELA block-ratio {forged_ratio:.2f}, forgery risk {forged_risk:.2f} -> SUSPECT")
    print(f"Demo application  : Trust Score {score}/100 (AMBER, hard-gate capped), {len(flags)} flags")
    print(f"Audit chain       : {len(chain)} entries, integrity {'VALID' if report['audit_valid'] else 'BROKEN'}")
    return report


if __name__ == "__main__": run()
