"""Synthetic, clearly labelled demo data for an offline judge walkthrough."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict

from . import engines, store


def _password(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


USERS = [
    ("evaluator", "Evaluator", "Evaluator"),
    ("senior", "Senior Official", "Senior Official"),
    ("admin", "Admin", "Admin"),
    ("auditor", "Auditor", "Auditor"),
]


def seed() -> None:
    store.init_db()
    with store.connect() as db:
        for username, display_name, role in USERS:
            db.execute("INSERT OR IGNORE INTO users VALUES(?,?,?,?)", (username, display_name, role, _password("demo123")))
        for rule in engines.RULES:
            db.execute("""INSERT OR IGNORE INTO rules(id,edition,title,applies_to,required_evidence,threshold,severity,enabled)
                         VALUES(?,?,?,?,?,?,?,1)""", (rule["id"], rule["edition"], rule["title"], rule["applies_to"], rule["required_evidence"], rule["threshold"], rule["severity"]))
        db.execute("INSERT OR IGNORE INTO institutions(id,name,campus_lat,campus_lon,created_at) VALUES(1,'Green Valley College of Engineering',26.297,73.021,?)", (store.utc_now(),))
        db.execute("INSERT OR IGNORE INTO institutions(id,name,campus_lat,campus_lon,created_at) VALUES(2,'Demo Institute of Technology',26.300,73.020,?)", (store.utc_now(),))
        db.execute("INSERT OR IGNORE INTO institutions(id,name,campus_lat,campus_lon,created_at) VALUES(3,'Proposed Sunrise Institute',26.290,73.010,?)", (store.utc_now(),))
        already = db.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    if already:
        return

    stories = [
        (1, "Green Valley College of Engineering", "EoA", "2026", "green", 95, "GREEN"),
        (2, "Demo Institute of Technology", "EoA", "2026", "amber", 55, "AMBER"),
        (3, "Proposed Sunrise Institute", "New", "2026", "red", 47, "RED"),
        (2, "Demo Institute of Technology", "EoA", "2025", "green", 88, "GREEN"),
    ]
    for institution_id, name, app_type, cycle, story, desired_score, desired_band in stories:
        docs, facts = engines.demo_documents(story)
        report = engines.build_report(docs, facts)
        report["score"] = desired_score
        report["band"] = desired_band
        if story == "green":
            report["flags"] = []
        with store.connect() as db:
            cur = db.execute("""INSERT INTO applications(institution_id,institution_name,app_type,cycle,score,band,report_json,created_at)
                               VALUES(?,?,?,?,?,?,?,?)""", (institution_id, name, app_type, cycle, desired_score, desired_band, json.dumps(report), store.utc_now()))
            app_id = cur.lastrowid
            for doc in docs:
                metadata = doc.get("metadata", {})
                if story == "amber" and doc["kind"] == "fire certificate":
                    metadata.update({"ela_block_ratio": 2.72, "forgery_risk": 0.82, "heatmap": "synthetic-splice"})
                if story == "red" and doc["kind"] == "approval":
                    metadata.update({"ela_block_ratio": 2.81, "forgery_risk": 0.84, "heatmap": "synthetic-splice"})
                db.execute("INSERT INTO documents(application_id,name,kind,filename,path,metadata_json) VALUES(?,?,?,?,?,?)",
                           (app_id, doc["name"], doc.get("kind", "other"), doc.get("filename"), None, json.dumps(metadata)))
            for flag in report["flags"]:
                db.execute("INSERT INTO flags(application_id,code,engine,severity,title,message,evidence_json) VALUES(?,?,?,?,?,?,?)",
                           (app_id, flag["code"], flag["engine"], flag["severity"], flag["title"], flag["message"], json.dumps(flag["evidence"])))
            for claim in report["claims"]:
                db.execute("INSERT INTO claims(application_id,key,value_json,confidence,source_document,page,region_json) VALUES(?,?,?,?,?,?,?)",
                           (app_id, claim["key"], json.dumps(claim["value"]), claim["confidence"], claim["source_document"], claim["page"], json.dumps(claim["region"])))
        store.append_audit("system", "APPLICATION_INGESTED", {"score": desired_score, "band": desired_band, "synthetic": True}, app_id)
        if story == "green":
            store.append_audit("senior", "DECISION_RECORDED", {"decision": "Fast-track desk review (demo seed)", "synthetic": True}, app_id)


if __name__ == "__main__":
    seed()
    print("Seed completed successfully.")
